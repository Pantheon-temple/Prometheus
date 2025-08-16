import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import AIMessage, ToolMessage

# 使用项目中的自定义模拟模型，支持工具调用
import sys
sys.path.append("/root/lix/Prometheus/")
from tests.test_utils.util import FakeListChatWithToolsModel

async def main():
    # 可以动态设置多个配置参数
    config = {
        "driver": "111111111111111111111",
        "timeout": 60,
        "max_retries": 5
    }
    # 将配置转换为命令行参数
    args = ["/root/lix/Prometheus/tests/tools/test_mcp_tools.py"]
    for key, value in config.items():
        args.extend([f"--{key}", str(value)])
    
    client = MultiServerMCPClient(
        {        
            "weather": {
                "command": "python",
                "args": args,
                "transport": "stdio",
            }
        }
    )
    
    # 异步获取工具
    tools = await client.get_tools()
    print(f"获取到的工具: {[tool.name for tool in tools]}")
    
    # 使用支持工具的模拟模型
    model = FakeListChatWithToolsModel(responses=["I need to check the weather for NYC"])
    
    # 创建工具节点
    tool_node = ToolNode(tools)
    
    def call_model(state: MessagesState):
        messages = state["messages"]
        
        # 检查是否已经有工具消息，如果有就结束
        if any(isinstance(msg, ToolMessage) for msg in messages):
            return {"messages": [AIMessage(content="Weather check completed!")]}
        
        # 第一次调用时创建工具调用响应
        response = AIMessage(
            content="Let me check the weather for you",
            tool_calls=[{
                "name": "get_weather",
                "args": {"location": "nyc"},
                "id": "call_1"
            }]
        )
        return {"messages": [response]}
    
    # 构建图
    builder = StateGraph(MessagesState)
    builder.add_node("call_model", call_model)
    builder.add_node("tools", tool_node)
    builder.add_edge(START, "call_model")
    builder.add_conditional_edges(
        "call_model",
        tools_condition,
    )
    builder.add_edge("tools", "call_model")
    
    graph = builder.compile()
    
    # 执行测试
    weather_response = await graph.ainvoke({"messages": "what is the weather in nyc?"})
    print("Response:", weather_response)
    
    return weather_response

# 运行异步主函数
if __name__ == "__main__":
    result = asyncio.run(main())