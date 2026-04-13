"""
重建Whoosh关键词索引

根据Chroma向量数据库中的数据重建Whoosh关键词索引。
直接使用Chroma原生API，不依赖项目封装。
"""

from __future__ import annotations

import logging
import os
import shutil
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_chroma_all_data():
    """获取Chroma中的所有文档数据 - 使用原生API"""
    import chromadb
    from pathlib import Path

    logger.info("直接连接Chroma数据库读取所有原始数据...")

    try:
        # 使用绝对路径，确保无论在哪里运行都能连接到正确的数据库
        script_dir = Path(__file__).parent.parent  # tests/rebuild_whoosh_index.py -> 项目根目录
        db_path = script_dir / "data" / "chroma_db"
        logger.info(f"数据库路径: {db_path}")
        
        # 直接使用Chroma原生API（完全绕过LangChain）
        client = chromadb.PersistentClient(path=str(db_path))
        
        # 列出所有集合
        collections = client.list_collections()
        logger.info(f"可用集合: {[c.name for c in collections]}")
        
        # 获取 rag_vectors 集合
        try:
            collection = client.get_collection("rag_vectors")
        except Exception as e:
            logger.error(f"获取集合 rag_vectors 失败: {e}")
            return []

        count = collection.count()
        logger.info(f"集合 rag_vectors 共有 {count} 条记录")

        if count == 0:
            logger.warning("集合为空，没有数据可索引")
            return []

        # 分批获取所有数据（避免一次性获取太多导致问题）
        all_ids = []
        all_documents = []
        all_metadatas = []
        
        batch_size = 100
        offset = 0
        
        while offset < count:
            logger.info(f"  读取中... {offset}/{count}")
            results = collection.get(
                limit=min(batch_size, count - offset),
                offset=offset,
                include=["documents", "metadatas"]
            )
            
            batch_ids = results.get('ids', [])
            if not batch_ids:
                break
                
            all_ids.extend(batch_ids)
            all_documents.extend(results.get('documents', []))
            all_metadatas.extend(results.get('metadatas', []))
            
            offset += len(batch_ids)
            
            if len(batch_ids) < batch_size:
                break

        logger.info(f"实际获取到 {len(all_ids)} 条记录")

        # 按 document_id 聚合内容
        doc_map = {}  # document_id -> {'content_parts': [], 'metadata': {}}

        for doc_id, content, metadata in zip(all_ids, all_documents, all_metadatas):
            if not metadata:
                continue

            document_id = metadata.get('document_id')
            if not document_id:
                # 如果没有 document_id，使用 chroma_id 作为唯一键
                document_id = doc_id

            if document_id not in doc_map:
                doc_map[document_id] = {
                    'content_parts': [],
                    'metadata': metadata,
                    'first_chroma_id': doc_id,
                }

            # 添加内容（即使是空的也记录，后面会处理）
            if content:
                doc_map[document_id]['content_parts'].append(content)

        # 转换为脚本需要的格式
        data_list = []
        for doc_id, data in doc_map.items():
            # 拼接所有分块内容
            full_content = '\n\n'.join(data['content_parts']) if data['content_parts'] else ""
            data_list.append({
                'chroma_id': data['first_chroma_id'],
                'content': full_content,
                'metadata': data['metadata'],
            })

        logger.info(f"成功读取 {len(data_list)} 个唯一文档")
        return data_list

    except Exception as e:
        logger.error(f"读取Chroma数据失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def chunk_data(data_list: list[dict], max_chunk_size: int = 1000) -> list[dict]:
    """
    将长文档分块

    Args:
        data_list: 原始数据列表
        max_chunk_size: 最大分块大小

    Returns:
        分块后的数据列表
    """
    chunked_data = []

    for item in data_list:
        content = item['content']
        metadata = item['metadata']
        chroma_id = item['chroma_id']

        # 跳过空内容
        if not content or not content.strip():
            logger.warning(f"文档 {chroma_id} 内容为空，跳过")
            continue

        # 如果内容较短，直接作为一个分块
        if len(content) <= max_chunk_size:
            chunked_data.append({
                'content': content,
                'metadata': metadata,
                'chroma_id': chroma_id,
                'chunk_index': 0,
            })
        else:
            # 按段落分块
            paragraphs = content.split('\n\n')
            current_chunk = []
            current_size = 0
            chunk_index = 0

            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue

                if current_size + len(para) > max_chunk_size and current_chunk:
                    # 保存当前分块
                    chunked_data.append({
                        'content': '\n\n'.join(current_chunk),
                        'metadata': metadata,
                        'chroma_id': chroma_id,
                        'chunk_index': chunk_index,
                    })
                    chunk_index += 1
                    current_chunk = [para]
                    current_size = len(para)
                else:
                    current_chunk.append(para)
                    current_size += len(para)

            # 保存最后一个分块
            if current_chunk:
                chunked_data.append({
                    'content': '\n\n'.join(current_chunk),
                    'metadata': metadata,
                    'chroma_id': chroma_id,
                    'chunk_index': chunk_index,
                })

    logger.info(f"分块完成: {len(data_list)}条 -> {len(chunked_data)}个分块")
    return chunked_data


def build_whoosh_index(chunked_data: list[dict]) -> int:
    """
    构建Whoosh索引

    Args:
        chunked_data: 分块后的数据列表

    Returns:
        成功索引的文档数
    """
    from app.config import get_sqlite_config
    from app.domain.rag.knowledge_base_type import KnowledgeBaseType
    from app.domain.rag.document_chunk import DocumentChunk
    from app.infrastructure.persistence.whoosh.whoosh_keyword_index import WhooshKeywordIndex

    # 获取索引路径
    sqlite_cfg = get_sqlite_config()
    db_path = sqlite_cfg.get("path", "./data/agent.db")
    index_dir = db_path.replace(".db", "_whoosh_index")

    logger.info(f"索引路径: {index_dir}")

    # 如果索引已存在，先删除
    if os.path.exists(index_dir):
        logger.info("删除旧索引...")
        shutil.rmtree(index_dir)

    # 创建索引实例
    keyword_index = WhooshKeywordIndex(index_dir=index_dir)

    # 按文档ID分组
    documents = {}
    for item in chunked_data:
        metadata = item['metadata']
        doc_id = metadata.get('document_id', item['chroma_id'])

        if doc_id not in documents:
            documents[doc_id] = {
                'chunks': [],
                'metadata': metadata,
            }

        chunk = DocumentChunk(
            content=item['content'],
            chunk_index=item['chunk_index'],
            metadata=metadata,
        )
        documents[doc_id]['chunks'].append(chunk)

    logger.info(f"准备索引 {len(documents)} 个文档...")

    # 添加到索引
    kb_type = KnowledgeBaseType.FAQ  # 默认使用FAQ类型

    success_count = 0
    for doc_id, doc_data in documents.items():
        try:
            keyword_index.add_document(
                document_id=doc_id,
                chunks=doc_data['chunks'],
                kb_type=kb_type,
            )
            success_count += 1
        except Exception as e:
            logger.error(f"索引文档 {doc_id} 失败: {e}")

    logger.info(f"索引构建完成: {success_count}/{len(documents)} 个文档")

    # 优化索引
    logger.info("优化索引...")
    keyword_index.optimize()

    return success_count


def verify_index():
    """验证索引是否正常工作"""
    from app.infrastructure.persistence.whoosh.whoosh_keyword_index import WhooshKeywordIndex

    logger.info("\n验证索引...")
    keyword_index = WhooshKeywordIndex()

    # 先查看索引中有哪些内容
    logger.info("查看索引中的所有分块...")
    all_results = keyword_index.search(query="*", top_k=100)
    logger.info(f"索引中共有 {len(all_results)} 个分块")
    for chunk_id, score in all_results[:5]:
        content = keyword_index.get_chunk_content(chunk_id)
        preview = content[:100] if content else "N/A"
        logger.info(f"  - {chunk_id}: {preview}...")

    # 测试搜索 - 使用从内容中提取的关键词
    test_queries = [
        "AI应用",
        "智能体",
        "工作流",
    ]

    logger.info("\n测试关键词搜索...")
    for query in test_queries:
        results = keyword_index.search(query=query, top_k=3)
        logger.info(f"查询 '{query}': 返回 {len(results)} 条结果")
        for chunk_id, score in results[:2]:
            content = keyword_index.get_chunk_content(chunk_id)
            preview = content[:80] if content else "N/A"
            logger.info(f"  - {chunk_id}: {score:.2f} | {preview}...")


def main():
    """主函数"""
    logger.info("=" * 70)
    logger.info("重建Whoosh关键词索引")
    logger.info("=" * 70)

    # 1. 读取Chroma数据
    data_list = get_chroma_all_data()
    if not data_list:
        logger.error("没有数据可索引")
        return 1

    # 2. 分块处理
    chunked_data = chunk_data(data_list)

    if not chunked_data:
        logger.error("分块后没有数据")
        return 1

    # 3. 构建Whoosh索引
    success_count = build_whoosh_index(chunked_data)

    if success_count == 0:
        logger.error("索引构建失败")
        return 1

    # 4. 验证索引
    verify_index()

    logger.info("\n" + "=" * 70)
    logger.info("Whoosh索引重建完成!")
    logger.info("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
