# weather_server.py
import sys
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Weather")

class WeatherTools:
    driver: str
    timeout: int
    max_retries: int
    
    @classmethod
    def configure(cls, **kwargs):
        """动态配置工具参数"""
        for key, value in kwargs.items():
            if hasattr(cls, key):
                setattr(cls, key, value)
                print(f"设置 {key} = {value}")
            else:
                print(f"警告: 未知参数 {key} = {value}")

    @staticmethod
    @mcp.tool()
    async def get_weather(location: str) -> str:
        """Get weather for a location."""
        return f"[Driver={WeatherTools.driver}, Timeout={WeatherTools.timeout}s] It's always sunny in {location}"

    @staticmethod
    @mcp.tool()
    async def get_temperature(location: str) -> str:
        """Get temperature for a location."""
        return f"[Driver={WeatherTools.driver}, Retries={WeatherTools.max_retries}] Temperature in {location} is 25°C"

def parse_args(args):
    """解析命令行参数为 kwargs"""
    kwargs = {}
    i = 1
    while i < len(args):
        if args[i].startswith("--"):
            key = args[i][2:]  # 移除 "--" 前缀
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                value = args[i + 1]
                # 尝试转换数据类型
                if value.isdigit():
                    value = int(value)
                elif value.lower() in ['true', 'false']:
                    value = value.lower() == 'true'
                kwargs[key] = value
                i += 2
            else:
                kwargs[key] = True  # 布尔标志
                i += 1
        else:
            i += 1
    return kwargs

if __name__ == "__main__":
    # 动态解析命令行参数
    # 支持格式：python test_mcp_tools.py --driver neo4j://server --timeout 60 --max_retries 5
    config = parse_args(sys.argv)
    if config:
        WeatherTools.configure(**config)
    # 启动 MCP
    mcp.run(transport="stdio")