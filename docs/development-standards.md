# 项目开发规范补充

## 测试脚本与工具开发规范

### 1. 路径使用规范

#### 必须使用绝对路径
- **禁止**在脚本中使用相对路径 `./data/`、`./config/` 等
- **必须**使用 `Path(__file__)` 计算绝对路径
- **必须**在脚本开头打印实际使用的路径

```python
from pathlib import Path

# ✅ 正确
PROJECT_ROOT = Path(__file__).parent.parent
db_path = (PROJECT_ROOT / "data" / "chroma_db").resolve()

# ❌ 错误
db_path = "./data/chroma_db"
```

### 2. 数据库连接规范

```python
def get_db_client():
    """获取数据库客户端"""
    import chromadb
    from pathlib import Path
    
    # 计算绝对路径
    script_dir = Path(__file__).parent.parent
    db_path = script_dir / "data" / "chroma_db"
    db_path = db_path.resolve()
    
    # 打印路径信息（必须）
    logger.info(f"数据库路径: {db_path}")
    logger.info(f"路径存在: {db_path.exists()}")
    
    client = chromadb.PersistentClient(path=str(db_path))
    
    # 验证连接（必须）
    collections = client.list_collections()
    logger.info(f"可用集合: {[c.name for c in collections]}")
    
    return client
```

### 3. 日志输出规范

测试脚本必须包含以下日志：
1. 脚本启动信息
2. 数据库路径
3. 连接状态
4. 数据量统计
5. 处理进度
6. 完成统计

```python
logger.info("=" * 60)
logger.info("开始重建索引")
logger.info("=" * 60)
logger.info(f"数据库路径: {db_path}")
logger.info(f"记录数: {count}")
logger.info(f"处理进度: {i}/{total}")
logger.info("重建完成")
```

### 4. 错误处理规范

```python
try:
    client = get_db_client()
    collection = client.get_collection("rag_vectors")
except Exception as e:
    logger.error(f"连接数据库失败: {e}")
    logger.error(f"请检查路径: {db_path}")
    logger.error(f"当前工作目录: {Path.cwd()}")
    raise
```

### 5. 验证检查清单

提交测试脚本前检查：
- [ ] 使用 `Path(__file__)` 获取绝对路径
- [ ] 脚本开头打印数据库路径
- [ ] 打印可用集合/表列表
- [ ] 验证记录数是否符合预期
- [ ] 提供清晰的错误信息

## 配置管理规范

### 路径配置

所有路径配置统一通过 `app.config` 管理：

```python
from app.config import get_chroma_config
from pathlib import Path

def get_db_path():
    config = get_chroma_config()
    path = Path(config.get("persist_directory"))
    
    # 转换为绝对路径
    if not path.is_absolute():
        from app.config import PROJECT_ROOT
        path = PROJECT_ROOT / path
    
    return path.resolve()
```

### 配置更新

需要在 `app/config.py` 中添加：

```python
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
```

## 禁止事项

1. **禁止**在脚本中硬编码相对路径
2. **禁止**假设脚本总是在项目根目录运行
3. **禁止**连接数据库前不打印路径信息
4. **禁止**不验证就直接处理数据
