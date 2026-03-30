"""
Agent 框架使用示例测试类

展示以下使用场景：
1. LLMFactory  —— 创建 LLM / Embedding 实例
2. ReactAgent  —— 同步 invoke / 异步 ainvoke / 流式 stream
3. 多轮对话    —— 通过 thread_id 保持上下文
4. 自定义 system_prompt 和工具列表
5. 动态扩展    —— add_tools / update_system_prompt
6. MCP 工具    —— ExampleMCPTool 独立调用 & 注入 Agent
7. Skill 技能  —— SummarizeSkill 独立调用 & 注入 Agent
8. DB 客户端   —— SQLite 写入/查询，MilvusClient 向量存储/检索
9. FastAPI 接口 —— 通过 httpx 调用 /chat、/tools、/health
"""

from __future__ import annotations

import asyncio
import logging
import sys
import os

# 将项目根目录加入 sys.path，使 `app` 包可以直接 import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("test_demo")


# ===========================================================================
# 1. LLMFactory 使用示例
# ===========================================================================

def demo_llm_factory() -> None:
    """演示如何通过工厂类创建 LLM 和 Embedding 实例"""
    logger.info("=" * 60)
    logger.info("【1】LLMFactory 示例")

    from app.llm.llm_factory import LLMFactory

    # 创建默认 LLM（deepseek-v3）
    llm = LLMFactory.create_llm()
    logger.info(f"默认 LLM 创建成功：model={llm.model_name}")

    # 创建指定模型
    llm_r1 = LLMFactory.create_llm("deepseek-r1")
    logger.info(f"deepseek-r1 创建成功：model={llm_r1.model_name}")

    # 创建 Ollama Embedding（需要本地 Ollama 服务运行）
    try:
        embedding = LLMFactory.create_embedding()
        logger.info(f"Embedding 模型创建成功：{embedding.model}")
    except Exception as e:
        logger.warning(f"Embedding 初始化跳过（Ollama 未运行）：{e}")


# ===========================================================================
# 2. ReactAgent 同步调用示例
# ===========================================================================

def demo_agent_invoke() -> None:
    """演示同步调用 ReactAgent.invoke()"""
    logger.info("=" * 60)
    logger.info("【2】ReactAgent 同步调用示例")

    from app.llm.llm_factory import LLMFactory
    from app.tools import ALL_TOOLS
    from app.agent.react_agent import ReactAgent

    llm = LLMFactory.create_llm("deepseek-v3")
    agent = ReactAgent(
        llm=llm,
        tools=ALL_TOOLS,
        system_prompt="你是一个智能助手，尽量简洁地回答用户问题。",
    )
    logger.info(f"Agent 工具列表：{[t.name for t in agent.tools]}")

    # 普通问答
    reply = agent.invoke("你好，介绍一下你自己")
    logger.info(f"Agent 回复：{reply}")

    # 触发计算器工具
    reply = agent.invoke("帮我计算 (256 + 128) * 3 的结果")
    logger.info(f"计算结果：{reply}")


# ===========================================================================
# 3. ReactAgent 异步调用示例
# ===========================================================================

async def demo_agent_ainvoke() -> None:
    """演示异步调用 ReactAgent.ainvoke()"""
    logger.info("=" * 60)
    logger.info("【3】ReactAgent 异步调用示例")

    from app.llm.llm_factory import LLMFactory
    from app.tools import ALL_TOOLS
    from app.agent.react_agent import ReactAgent

    llm = LLMFactory.create_llm("deepseek-v3")
    agent = ReactAgent(llm=llm, tools=ALL_TOOLS)

    reply = await agent.ainvoke("Python 和 Java 的主要区别是什么？")
    logger.info(f"异步回复：{reply}")


# ===========================================================================
# 4. 多轮对话示例（同一 thread_id 保持上下文）
# ===========================================================================

def demo_multi_turn() -> None:
    """演示多轮对话，相同 thread_id 共享对话上下文"""
    logger.info("=" * 60)
    logger.info("【4】多轮对话示例")

    from app.llm.llm_factory import LLMFactory
    from app.tools import ALL_TOOLS
    from app.agent.react_agent import ReactAgent

    llm = LLMFactory.create_llm("deepseek-v3")
    agent = ReactAgent(llm=llm, tools=ALL_TOOLS)

    thread = "user-demo-001"

    r1 = agent.invoke("我的名字叫小明，我今年 25 岁", thread_id=thread)
    logger.info(f"第1轮：{r1}")

    r2 = agent.invoke("我叫什么名字？今年几岁？", thread_id=thread)
    logger.info(f"第2轮：{r2}")

    # 不同 thread_id 不共享上下文
    r3 = agent.invoke("我叫什么名字？", thread_id="other-session")
    logger.info(f"另一会话（应不记得名字）：{r3}")


# ===========================================================================
# 5. 自定义 system_prompt 和工具列表
# ===========================================================================

def demo_custom_prompt_and_tools() -> None:
    """演示自定义系统提示词，及只传入部分工具"""
    logger.info("=" * 60)
    logger.info("【5】自定义 system_prompt + 工具列表示例")

    from app.llm.llm_factory import LLMFactory
    from app.tools.calculator_tool import calculator
    from app.agent.react_agent import ReactAgent

    llm = LLMFactory.create_llm("deepseek-v3")

    # 仅赋予计算器工具，使用专属系统提示词
    agent = ReactAgent(
        llm=llm,
        tools=[calculator],
        system_prompt="你是一个专业的数学计算助手，只负责帮用户做数学运算，其他话题礼貌拒绝。",
    )
    logger.info(f"当前系统提示词：{agent.system_prompt}")
    logger.info(f"当前工具：{[t.name for t in agent.tools]}")

    reply = agent.invoke("请计算 1024 / 32")
    logger.info(f"回复：{reply}")


# ===========================================================================
# 6. 动态扩展：add_tools / update_system_prompt
# ===========================================================================

def demo_dynamic_extension() -> None:
    """演示运行时动态添加工具和更新系统提示词"""
    logger.info("=" * 60)
    logger.info("【6】动态扩展示例")

    from app.llm.llm_factory import LLMFactory
    from app.tools.calculator_tool import calculator
    from app.tools.search_tool import search
    from app.agent.react_agent import ReactAgent

    llm = LLMFactory.create_llm("deepseek-v3")
    agent = ReactAgent(llm=llm, tools=[calculator])
    logger.info(f"初始工具：{[t.name for t in agent.tools]}")

    # 动态添加搜索工具
    agent.add_tools([search])
    logger.info(f"添加后工具：{[t.name for t in agent.tools]}")

    # 动态更新系统提示词
    agent.update_system_prompt("你是一个升级后的多功能助手，支持计算和搜索。")
    logger.info(f"更新后提示词：{agent.system_prompt}")


# ===========================================================================
# 7. 流式输出示例
# ===========================================================================

def demo_stream() -> None:
    """演示流式调用，逐步打印每个推理步骤"""
    logger.info("=" * 60)
    logger.info("【7】流式调用示例")

    from app.llm.llm_factory import LLMFactory
    from app.tools import ALL_TOOLS
    from app.agent.react_agent import ReactAgent
    from langchain_core.messages import AIMessage, ToolMessage

    llm = LLMFactory.create_llm("deepseek-v3")
    agent = ReactAgent(llm=llm, tools=ALL_TOOLS)

    print("\n--- 流式输出开始 ---")
    for chunk in agent.stream("帮我计算 99 * 88，并告诉我结果"):
        messages = chunk.get("messages", [])
        if messages:
            last = messages[-1]
            msg_type = type(last).__name__
            content = getattr(last, "content", "")
            if content:
                print(f"[{msg_type}] {str(content)[:200]}")
    print("--- 流式输出结束 ---\n")


# ===========================================================================
# 8. MCP 工具使用示例
# ===========================================================================

def demo_mcp_tool() -> None:
    """演示 MCP 工具的独立调用与注入 Agent"""
    logger.info("=" * 60)
    logger.info("【8】MCP 工具示例")

    from app.mcp.example_mcp import ExampleMCPTool, get_weather

    # 直接调用 MCP 工具
    mcp_tool = ExampleMCPTool()
    result = mcp_tool.run(city="上海")
    logger.info(f"MCP 直接调用结果：{result}")

    # 已转换为 LangChain 工具的版本
    result2 = get_weather.invoke({"city": "北京"})
    logger.info(f"LangChain 工具调用结果：{result2}")

    # 将 MCP 工具注入 Agent
    from app.llm.llm_factory import LLMFactory
    from app.agent.react_agent import ReactAgent

    llm = LLMFactory.create_llm("deepseek-v3")
    agent = ReactAgent(
        llm=llm,
        tools=[get_weather],
        system_prompt="你是一个天气助手，使用工具查询天气。",
    )
    reply = agent.invoke("广州今天天气怎么样？")
    logger.info(f"Agent 天气查询结果：{reply}")


# ===========================================================================
# 9. Skill 技能使用示例
# ===========================================================================

def demo_skill() -> None:
    """演示 Skill 的独立调用与注入 Agent"""
    logger.info("=" * 60)
    logger.info("【9】Skill 技能示例")

    from app.skills.example_skill import SummarizeSkill, summarize_text

    # 直接调用 Skill
    skill = SummarizeSkill()
    long_text = (
        "人工智能（Artificial Intelligence，AI）是计算机科学的一个分支，"
        "它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。"
        "该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。"
        "人工智能从诞生以来，理论和技术日益成熟，应用领域也不断扩大，"
        "可以设想，未来人工智能带来的科技产品，将会是人类智慧的\"容器\"。"
    )
    result = skill.execute(text=long_text)
    logger.info(f"Skill 直接调用结果：\n{result}")

    # 已转换为 LangChain 工具的版本
    result2 = summarize_text.invoke({"text": long_text[:50]})
    logger.info(f"LangChain 工具调用结果：{result2}")

    # 将 Skill 注入 Agent
    from app.llm.llm_factory import LLMFactory
    from app.agent.react_agent import ReactAgent

    llm = LLMFactory.create_llm("deepseek-v3")
    agent = ReactAgent(
        llm=llm,
        tools=[summarize_text],
        system_prompt="你是一个文本摘要助手，使用工具对用户提供的文本生成摘要。",
    )
    reply = agent.invoke(f"请帮我对以下文字做摘要：{long_text}")
    logger.info(f"Agent 摘要结果：{reply}")


# ===========================================================================
# 10. SQLite 客户端使用示例
# ===========================================================================

def demo_sqlite() -> None:
    """演示 SQLite 客户端的基础操作"""
    logger.info("=" * 60)
    logger.info("【10】SQLite 客户端示例")

    from app.db.sqlite_client import SQLiteClient

    db = SQLiteClient()

    # 建表
    db.execute("""
        CREATE TABLE IF NOT EXISTS demo_users (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            name   TEXT NOT NULL,
            age    INTEGER,
            remark TEXT
        )
    """)
    logger.info("表 demo_users 创建成功（已存在则跳过）")

    # 插入数据
    db.execute(
        "INSERT INTO demo_users (name, age, remark) VALUES (?, ?, ?)",
        ("张三", 28, "测试用户A"),
    )
    db.execute(
        "INSERT INTO demo_users (name, age, remark) VALUES (?, ?, ?)",
        ("李四", 32, "测试用户B"),
    )
    logger.info("插入 2 条测试数据")

    # 查询所有
    rows = db.fetchall("SELECT id, name, age, remark FROM demo_users")
    logger.info(f"查询结果（共 {len(rows)} 条）：")
    for row in rows:
        logger.info(f"  {dict(row)}")

    # 条件查询
    row = db.fetchone("SELECT * FROM demo_users WHERE name = ?", ("张三",))
    logger.info(f"查询张三：{dict(row) if row else '未找到'}")

    # 清理测试数据
    db.execute("DROP TABLE IF EXISTS demo_users")
    logger.info("测试表已清理")


# ===========================================================================
# 11. Milvus 向量客户端使用示例
# ===========================================================================

def demo_milvus() -> None:
    """演示 MilvusClient 向量存储与检索"""
    logger.info("=" * 60)
    logger.info("【11】Milvus 向量客户端示例")

    from app.db.milvus_client import MilvusClient

    client = MilvusClient()

    collection_name = "demo_collection"
    dim = 4  # 演示用低维向量

    # 创建集合
    client.create_collection(collection_name=collection_name, dim=dim)
    logger.info(f"集合 '{collection_name}' 创建成功")

    # 插入向量
    vectors = [
        [0.1, 0.2, 0.3, 0.4],
        [0.5, 0.6, 0.7, 0.8],
        [0.9, 0.1, 0.2, 0.3],
    ]
    payloads = [
        {"text": "第一条文档：Python 是一种编程语言"},
        {"text": "第二条文档：LangChain 是 AI 应用框架"},
        {"text": "第三条文档：Milvus 是向量数据库"},
    ]
    client.insert(collection_name, vectors, payloads)
    logger.info(f"插入 {len(vectors)} 条向量数据")

    # 相似度搜索
    query_vector = [0.1, 0.2, 0.3, 0.4]
    results = client.search(collection_name, query_vector, top_k=2)
    logger.info(f"向量检索结果（top_k=2）：")
    for res in results:
        logger.info(f"  {res}")

    # 删除集合（清理）
    client.drop_collection(collection_name)
    logger.info(f"集合 '{collection_name}' 已删除")


# ===========================================================================
# 12. FastAPI HTTP 接口调用示例（需要服务已启动）
# ===========================================================================

def demo_http_api(base_url: str = "http://127.0.0.1:8000") -> None:
    """
    演示通过 httpx 调用 FastAPI 接口

    前提：需要先启动服务 `uv run python main.py`
    """
    logger.info("=" * 60)
    logger.info("【12】FastAPI HTTP 接口示例")

    try:
        import httpx
    except ImportError:
        logger.warning("httpx 未安装，跳过 HTTP 接口示例。可通过 `uv add httpx` 安装")
        return

    with httpx.Client(base_url=base_url, timeout=60) as client:
        # 健康检查
        resp = client.get("/api/v1/health")
        logger.info(f"健康检查：{resp.json()}")

        # 查询工具列表
        resp = client.get("/api/v1/tools")
        tools = resp.json()
        logger.info(f"可用工具（共 {len(tools)} 个）：")
        for t in tools:
            logger.info(f"  - {t['name']}: {t['description'][:50]}")

        # 普通对话
        resp = client.post(
            "/api/v1/chat",
            json={
                "message": "帮我计算 7 的阶乘",
                "model": "deepseek-v3",
                "thread_id": "http-test-001",
            },
        )
        data = resp.json()
        logger.info(f"对话回复：{data['reply']}")

        # 多轮对话
        resp2 = client.post(
            "/api/v1/chat",
            json={
                "message": "上一道题的结果乘以 2 是多少？",
                "model": "deepseek-v3",
                "thread_id": "http-test-001",   # 相同 thread_id
            },
        )
        logger.info(f"多轮对话回复：{resp2.json()['reply']}")


# ===========================================================================
# 13. 完整集成测试：Agent + MCP + Skill + 所有工具
# ===========================================================================

def demo_full_integration() -> None:
    """演示将所有工具（基础工具 + MCP + Skill）统一注入 Agent"""
    logger.info("=" * 60)
    logger.info("【13】完整集成示例")

    from app.llm.llm_factory import LLMFactory
    from app.tools import ALL_TOOLS
    from app.mcp.example_mcp import get_weather
    from app.skills.example_skill import summarize_text
    from app.agent.react_agent import ReactAgent

    llm = LLMFactory.create_llm("deepseek-v3")

    # 组合所有工具
    all_tools = ALL_TOOLS + [get_weather, summarize_text]

    agent = ReactAgent(
        llm=llm,
        tools=all_tools,
        system_prompt=(
            "你是一个全能助手，可以进行数学计算、网络搜索、向量检索、"
            "查询天气和文本摘要。请根据用户需求自动选择合适的工具完成任务。"
        ),
    )

    logger.info(f"集成 Agent 工具列表：{[t.name for t in agent.tools]}")

    # 测试天气查询
    r1 = agent.invoke("上海今天天气怎么样？")
    logger.info(f"天气问答：{r1}")

    # 测试计算
    r2 = agent.invoke("请计算 2 的 10 次方")
    logger.info(f"计算问答：{r2}")


# ===========================================================================
# 主入口：选择要运行的示例
# ===========================================================================

def run_all_local_demos() -> None:
    """
    运行所有不依赖外部服务的本地示例
    （跳过 Milvus、HTTP 接口等需要服务的示例）
    """
    demos = [
        ("LLMFactory 工厂类", demo_llm_factory),
        ("MCP 工具", demo_mcp_tool),
        ("Skill 技能", demo_skill),
        ("SQLite 客户端", demo_sqlite),
    ]
    for name, fn in demos:
        try:
            fn()
        except Exception as e:
            logger.error(f"示例【{name}】执行失败：{e}", exc_info=True)


async def run_all_agent_demos() -> None:
    """
    运行所有 Agent 相关示例（需要阿里百炼 API Key 配置正确）
    """
    demos = [
        ("ReactAgent 同步调用", demo_agent_invoke),
        ("多轮对话", demo_multi_turn),
        ("自定义提示词+工具", demo_custom_prompt_and_tools),
        ("动态扩展", demo_dynamic_extension),
        ("流式输出", demo_stream),
        ("完整集成", demo_full_integration),
    ]
    for name, fn in demos:
        try:
            fn()
        except Exception as e:
            logger.error(f"示例【{name}】执行失败：{e}", exc_info=True)

    # 异步示例
    try:
        await demo_agent_ainvoke()
    except Exception as e:
        logger.error(f"示例【ReactAgent 异步调用】执行失败：{e}", exc_info=True)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Agent 框架使用示例")
    parser.add_argument(
        "--mode",
        choices=["local", "agent", "http", "milvus", "all"],
        default="local",
        help=(
            "运行模式：\n"
            "  local  - 本地示例（LLM工厂/MCP/Skill/SQLite），无需 API Key\n"
            "  agent  - Agent 示例（需要阿里百炼 API Key）\n"
            "  http   - HTTP 接口示例（需要先启动 main.py 服务）\n"
            "  milvus - Milvus 向量库示例\n"
            "  all    - 运行全部示例\n"
        ),
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="FastAPI 服务地址（http 模式下使用）",
    )
    args = parser.parse_args()

    if args.mode == "local":
        run_all_local_demos()

    elif args.mode == "agent":
        asyncio.run(run_all_agent_demos())

    elif args.mode == "http":
        demo_http_api(base_url=args.base_url)

    elif args.mode == "milvus":
        demo_milvus()

    elif args.mode == "all":
        run_all_local_demos()
        asyncio.run(run_all_agent_demos())
        demo_milvus()
        demo_http_api(base_url=args.base_url)
