# 数据库路径配置与测试脚本编写规范

## 问题背景

在开发 `rebuild_whoosh_index.py` 脚本过程中，遇到了因使用相对路径导致脚本在不同运行环境下连接不同数据库的问题。本文档总结教训，制定规范避免类似问题再次发生。

## 核心问题

**相对路径的风险**：
```python
# ❌ 错误 - 相对路径依赖运行时的 working directory
client = chromadb.PersistentClient(path="./data/chroma_db")

# 如果脚本在 tests/ 目录运行，会连接到 tests/data/chroma_db
# 如果脚本在项目根目录运行，会连接到 ./data/chroma_db
```

**不同运行环境的影响**：
- PyCharm 运行按钮可能设置不同的 working directory
- 命令行运行 vs IDE 运行路径可能不同
- 子目录运行脚本会导致路径解析错误

## 规范要求

### 1. 数据库连接必须使用绝对路径

```python
from pathlib import Path
import chromadb

# ✅ 正确 - 使用基于脚本位置的绝对路径
def get_db_client():
    # 获取脚本所在目录
    script_dir = Path(__file__).parent
    # 构建数据库路径
    db_path = script_dir / ".." / "data" / "chroma_db"
    db_path = db_path.resolve()  # 转换为绝对路径
    
    return chromadb.PersistentClient(path=str(db_path))
```

### 2. 或者使用配置中心统一路径管理

```python
from app.config import get_config
from pathlib import Path

def get_db_path():
    """从配置获取数据库路径并确保是绝对路径"""
    config = get_config()
    persist_dir = config.get("chroma", {}).get("persist_directory", "./data/chroma_db")
    
    # 转换为绝对路径
    path = Path(persist_dir)
    if not path.is_absolute():
        # 相对于项目根目录
        project_root = Path(__file__).parent.parent.parent
        path = project_root / path
    
    return path.resolve()
```

### 3. 测试脚本必须打印路径信息

```python
def get_chroma_all_data():
    """获取Chroma数据 - 带路径验证"""
    import chromadb
    from pathlib import Path
    
    # 计算并打印路径
    script_dir = Path(__file__).parent.parent
    db_path = script_dir / "data" / "chroma_db"
    db_path = db_path.resolve()
    
    logger.info(f"数据库路径: {db_path}")
    logger.info(f"路径是否存在: {db_path.exists()}")
    
    client = chromadb.PersistentClient(path=str(db_path))
    
    # 验证连接
    collections = client.list_collections()
    logger.info(f"可用集合: {[c.name for c in collections]}")
    
    return client
```

### 4. 路径配置规范

#### 项目结构约定
```
my-agent/
├── data/                    # 数据库目录（在 .gitignore 中）
│   ├── chroma_db/          # Chroma 向量数据库
│   ├── agent_whoosh_index/ # Whoosh 索引
│   └── agent.db            # SQLite 数据库
├── tests/                  # 测试脚本
│   └── rebuild_whoosh_index.py
└── app/
    └── config.py           # 配置中心
```

#### 配置文件规范
```toml
# application.toml
[database.chroma]
# 使用相对于项目根目录的路径
persist_directory = "./data/chroma_db"
collection_name = "rag_vectors"

[database.sqlite]
path = "./data/agent.db"
```

#### 路径解析代码
```python
# app/config.py
from pathlib import Path

# 项目根目录（config.py 的上级目录）
PROJECT_ROOT = Path(__file__).parent.parent

def resolve_path(path_str: str) -> Path:
    """
    将配置中的相对路径解析为绝对路径
    
    规则：
    1. 如果已是绝对路径，直接返回
    2. 如果是相对路径，相对于项目根目录解析
    """
    path = Path(path_str)
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()
```

## 测试脚本编写检查清单

### 运行前检查
- [ ] 脚本是否使用绝对路径连接数据库？
- [ ] 脚本是否打印实际连接的数据库路径？
- [ ] 脚本是否验证数据库连接成功？
- [ ] 脚本是否在开头列出可用的集合/表？

### 代码审查检查
- [ ] 没有硬编码的 `./data` 或 `./config` 等相对路径
- [ ] 所有路径都通过 `Path(__file__)` 或配置中心获取
- [ ] 数据库操作有详细的日志输出
- [ ] 失败时有清晰的错误信息

## 示例：规范的重建脚本

```python
"""
重建Whoosh关键词索引

运行方式:
    uv run python tests/rebuild_whoosh_index.py
"""
from __future__ import annotations

import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 项目根目录（本脚本位于 tests/ 目录）
PROJECT_ROOT = Path(__file__).parent.parent

def get_chroma_client():
    """获取Chroma客户端 - 使用绝对路径"""
    import chromadb
    
    # 构建绝对路径
    db_path = (PROJECT_ROOT / "data" / "chroma_db").resolve()
    
    logger.info(f"连接数据库: {db_path}")
    logger.info(f"路径存在: {db_path.exists()}")
    
    client = chromadb.PersistentClient(path=str(db_path))
    
    # 验证连接
    collections = client.list_collections()
    logger.info(f"可用集合: {[c.name for c in collections]}")
    
    return client

def main():
    client = get_chroma_client()
    collection = client.get_collection("rag_vectors")
    
    count = collection.count()
    logger.info(f"集合记录数: {count}")
    
    # ... 后续处理

if __name__ == "__main__":
    main()
```

## 教训总结

### 这次的问题
1. 使用了相对路径 `./data/chroma_db`
2. 假设脚本总是在项目根目录运行
3. 没有在开头打印实际连接的路径
4. 没有验证集合列表是否符合预期

### 避免的方案
1. **强制使用绝对路径** - 基于 `Path(__file__)` 计算
2. **增加路径日志** - 连接前打印完整路径
3. **验证环境** - 列出集合、记录数等验证信息
4. **统一配置** - 通过配置中心管理所有路径

## 相关文档

- [DDD 架构设计](./ddd-architecture.md)
- [RAG 架构设计](./rag-architecture.md)
