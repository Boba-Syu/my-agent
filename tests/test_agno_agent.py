"""
Agno Agent 单元测试

测试工具包装器的参数传递逻辑
"""
from __future__ import annotations

import sys
sys.path.insert(0, 'c:/Users/19148/PycharmProjects/my-agent')

from app.domain.agent.agent_tool import AgentTool, ToolResult
from app.infrastructure.llm.llm_provider import LLMConfig


class TestStatsTool(AgentTool):
    """模拟 StatsByPeriodTool"""
    
    @property
    def name(self) -> str:
        return "stats_by_period"
    
    @property
    def description(self) -> str:
        return "统计工具"
    
    def execute(self, start_date: str, end_date: str) -> ToolResult:
        return ToolResult.success_result(f"统计 {start_date} 到 {end_date}")


class TestNoArgsTool(AgentTool):
    """无参数工具"""
    
    @property
    def name(self) -> str:
        return "no_args_tool"
    
    @property
    def description(self) -> str:
        return "无参数工具"
    
    def execute(self) -> ToolResult:
        return ToolResult.success_result("无参数执行成功")


class TestKwargsTool(AgentTool):
    """接受 **kwargs 的工具"""
    
    @property
    def name(self) -> str:
        return "kwargs_tool"
    
    @property
    def description(self) -> str:
        return "接受任意参数"
    
    def execute(self, **kwargs) -> ToolResult:
        return ToolResult.success_result(f"收到参数: {kwargs}")


class TestMixedTool(AgentTool):
    """混合参数工具"""
    
    @property
    def name(self) -> str:
        return "mixed_tool"
    
    @property
    def description(self) -> str:
        return "混合参数"
    
    def execute(self, name: str, **kwargs) -> ToolResult:
        return ToolResult.success_result(f"name={name}, kwargs={kwargs}")


def create_test_agent(tools):
    """创建测试用的 AgnoAgent"""
    from app.infrastructure.agent.agno.agno_agent import AgnoAgent
    
    llm_config = LLMConfig(
        model="deepseek-v3",
        api_key="test",
        base_url="https://test.com"
    )
    
    return AgnoAgent(
        llm_config=llm_config,
        system_prompt="测试",
        tools=tools
    )


def test_normal_kwargs():
    """测试普通关键字参数"""
    print("\n=== 测试: 普通关键字参数 ===")
    tool = TestStatsTool()
    agent = create_test_agent([tool])
    wrapped = agent._wrap_tool_for_agno(tool)
    
    result = wrapped(start_date="2024-01-01", end_date="2024-01-31")
    assert "2024-01-01" in result, f"结果应包含 start_date: {result}"
    assert "2024-01-31" in result, f"结果应包含 end_date: {result}"
    print(f"  PASS: {result}")


def test_camel_case_kwargs():
    """测试驼峰命名参数"""
    print("\n=== 测试: 驼峰命名参数 ===")
    tool = TestStatsTool()
    agent = create_test_agent([tool])
    wrapped = agent._wrap_tool_for_agno(tool)
    
    result = wrapped(startDate="2024-02-01", endDate="2024-02-28")
    assert "2024-02-01" in result, f"结果应包含 start_date: {result}"
    assert "2024-02-28" in result, f"结果应包含 end_date: {result}"
    print(f"  PASS: {result}")


def test_positional_args():
    """测试位置参数"""
    print("\n=== 测试: 位置参数 ===")
    tool = TestStatsTool()
    agent = create_test_agent([tool])
    wrapped = agent._wrap_tool_for_agno(tool)
    
    result = wrapped("2024-03-01", "2024-03-31")
    assert "2024-03-01" in result, f"结果应包含 start_date: {result}"
    assert "2024-03-31" in result, f"结果应包含 end_date: {result}"
    print(f"  PASS: {result}")


def test_agno_nested_kwargs_only():
    """测试 Agno 嵌套结构（仅 kwargs）"""
    print("\n=== 测试: Agno 嵌套结构（仅 kwargs） ===")
    tool = TestStatsTool()
    agent = create_test_agent([tool])
    wrapped = agent._wrap_tool_for_agno(tool)
    
    # 模拟 Agno 调用: wrapped_tool(args={}, kwargs={'start_date': '...'})
    result = wrapped(args={}, kwargs={'start_date': '2024-04-01', 'end_date': '2024-04-30'})
    assert "2024-04-01" in result, f"结果应包含 start_date: {result}"
    assert "2024-04-30" in result, f"结果应包含 end_date: {result}"
    print(f"  PASS: {result}")


def test_agno_nested_args_only():
    """测试 Agno 嵌套结构（仅 args）"""
    print("\n=== 测试: Agno 嵌套结构（仅 args） ===")
    tool = TestStatsTool()
    agent = create_test_agent([tool])
    wrapped = agent._wrap_tool_for_agno(tool)
    
    result = wrapped(args={'start_date': '2024-05-01', 'end_date': '2024-05-31'}, kwargs={})
    assert "2024-05-01" in result, f"结果应包含 start_date: {result}"
    assert "2024-05-31" in result, f"结果应包含 end_date: {result}"
    print(f"  PASS: {result}")


def test_agno_args_in_kwargs_only():
    """测试 Agno 只传 args 在 kwargs 中的情况（日志中的实际场景）"""
    print("\n=== 测试: Agno 只传 args（日志场景） ===")
    tool = TestStatsTool()
    agent = create_test_agent([tool])
    wrapped = agent._wrap_tool_for_agno(tool)
    
    # 模拟日志中的情况: kwargs={'args': {'start_date': '...', 'end_date': '...'}}
    result = wrapped(args={'start_date': '2024-08-01', 'end_date': '2024-08-31'})
    assert "2024-08-01" in result, f"结果应包含 start_date: {result}"
    assert "2024-08-31" in result, f"结果应包含 end_date: {result}"
    print(f"  PASS: {result}")


def test_agno_nested_mixed():
    """测试 Agno 嵌套结构（args + kwargs 混合）"""
    print("\n=== 测试: Agno 嵌套结构（混合） ===")
    tool = TestStatsTool()
    agent = create_test_agent([tool])
    wrapped = agent._wrap_tool_for_agno(tool)
    
    result = wrapped(args={'start_date': '2024-06-01'}, kwargs={'end_date': '2024-06-30'})
    assert "2024-06-01" in result, f"结果应包含 start_date: {result}"
    assert "2024-06-30" in result, f"结果应包含 end_date: {result}"
    print(f"  PASS: {result}")


def test_agno_nested_camel_case():
    """测试 Agno 嵌套结构（驼峰命名）"""
    print("\n=== 测试: Agno 嵌套结构（驼峰命名） ===")
    tool = TestStatsTool()
    agent = create_test_agent([tool])
    wrapped = agent._wrap_tool_for_agno(tool)
    
    result = wrapped(args={}, kwargs={'startDate': '2024-07-01', 'endDate': '2024-07-31'})
    assert "2024-07-01" in result, f"结果应包含 start_date: {result}"
    assert "2024-07-31" in result, f"结果应包含 end_date: {result}"
    print(f"  PASS: {result}")


def test_agno_empty_nested():
    """测试 Agno 空嵌套结构（返回友好错误提示）"""
    print("\n=== 测试: Agno 空嵌套结构 ===")
    tool = TestStatsTool()
    agent = create_test_agent([tool])
    wrapped = agent._wrap_tool_for_agno(tool)
    
    result = wrapped(args={}, kwargs={})
    assert "参数错误" in result, f"应返回参数错误: {result}"
    assert "start_date" in result, f"错误应提示 start_date: {result}"
    assert "end_date" in result, f"错误应提示 end_date: {result}"
    print(f"  PASS: 正确处理空参数 -> {result}")


def test_no_args_tool():
    """测试无参数工具"""
    print("\n=== 测试: 无参数工具 ===")
    tool = TestNoArgsTool()
    agent = create_test_agent([tool])
    wrapped = agent._wrap_tool_for_agno(tool)
    
    result = wrapped()
    assert "无参数执行成功" in result, f"结果: {result}"
    print(f"  PASS: {result}")


def test_kwargs_tool():
    """测试 **kwargs 工具"""
    print("\n=== 测试: **kwargs 工具 ===")
    tool = TestKwargsTool()
    agent = create_test_agent([tool])
    wrapped = agent._wrap_tool_for_agno(tool)
    
    result = wrapped(foo="bar", count=42)
    assert "foo" in result, f"结果应包含 foo: {result}"
    assert "bar" in result, f"结果应包含 bar: {result}"
    print(f"  PASS: {result}")


def test_mixed_tool():
    """测试混合参数工具"""
    print("\n=== 测试: 混合参数工具 ===")
    tool = TestMixedTool()
    agent = create_test_agent([tool])
    wrapped = agent._wrap_tool_for_agno(tool)
    
    result = wrapped(name="test", extra="value")
    assert "name=test" in result, f"结果应包含 name: {result}"
    assert "extra" in result, f"结果应包含 extra: {result}"
    print(f"  PASS: {result}")


def test_mixed_tool_agno_nested():
    """测试混合参数工具的 Agno 嵌套调用"""
    print("\n=== 测试: 混合参数工具（Agno 嵌套） ===")
    tool = TestMixedTool()
    agent = create_test_agent([tool])
    wrapped = agent._wrap_tool_for_agno(tool)
    
    result = wrapped(args={}, kwargs={'name': 'nested', 'extra': 'data'})
    assert "name=nested" in result, f"结果应包含 name: {result}"
    assert "extra" in result, f"结果应包含 extra: {result}"
    print(f"  PASS: {result}")


def run_all_tests():
    """运行所有测试"""
    print("="*60)
    print("Agno Agent 工具包装器测试")
    print("="*60)
    
    tests = [
        test_normal_kwargs,
        test_camel_case_kwargs,
        test_positional_args,
        test_agno_nested_kwargs_only,
        test_agno_nested_args_only,
        test_agno_args_in_kwargs_only,  # 新测试
        test_agno_nested_mixed,
        test_agno_nested_camel_case,
        test_agno_empty_nested,
        test_no_args_tool,
        test_kwargs_tool,
        test_mixed_tool,
        test_mixed_tool_agno_nested,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
