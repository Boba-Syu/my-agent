print("=" * 60)
print("【2】ReactAgent 同步调用示例")

from app.llm.llm_factory import LLMFactory
from app.tools import ALL_TOOLS
from app.agent.react_agent import ReactAgent

llm = LLMFactory.create_llm("deepseek-v3")
agent = ReactAgent(
    llm=llm,
    tools=ALL_TOOLS,
    system_prompt="你是一个智能助手，尽量简洁地回答用户问题。",
)
print(f"Agent 工具列表：{[t.name for t in agent.tools]}")

# 普通问答
reply = agent.invoke("你好，介绍一下你自己")
print(f"Agent 回复：{reply}")

# 触发计算器工具
reply = agent.invoke("帮我计算 (256 + 128) * 3 的结果")
print(f"计算结果：{reply}")
