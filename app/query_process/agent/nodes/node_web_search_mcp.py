import asyncio
import json
import sys
from agents.mcp import MCPServerStreamableHttp
from app.core.logger import  logger

from app.conf.bailian_mcp_config import mcp_config
from app.utils.task_utils import add_running_task,add_done_task

DASHSCOPE_BASE_URL_STREAMABLE = mcp_config.mcp_base_url
DASHSCOPE_API_KEY = mcp_config.api_key


async def mcp_call_streamable(query):
    """
    调用百炼的网络搜索工具
    :param query:
    :return:
    """
    # 1. 创建MCPServerStreamableHttp对象
    search_mcp = MCPServerStreamableHttp(
        name = "search_mcp",
        params={
            # 核心参数
            "url": DASHSCOPE_BASE_URL_STREAMABLE,
            "headers": {"Authorization": f"Bearer {DASHSCOPE_API_KEY}"},
            "timeout": 10, #连接超时时间
        },
        max_retry_attempts=3
    )
    # 2. 连接 - 调用 - 关闭
    try:
        # 连接
        await search_mcp.connect()

        # 获取工具
        tools = await search_mcp.list_tools()
        print(f"工具列表：{tools}")
        # 调用
        result = await search_mcp.call_tool(
            tool_name="bailian_web_search",
            arguments={
                "query": query,
                "count": 5,
            }
        )
        return result
    finally:
        await search_mcp.cleanup()


def node_web_search_mcp(state):
    """
    节点功能，调用外部搜索引擎补充信息
    :param state:
    :return:
    """
    add_running_task(state["session_id"], sys._getframe().f_code.co_name,state["is_stream"])
    print("---node-web-search-mcp处理---")

    # 1. 获取问题 （rewritten_query）
    query = state.get("rewritten_query")
    # 2. 调用streamable网络搜索方法
    result = asyncio.run(mcp_call_streamable(query))
    # 3. 结果处理即可
    # {
    #   "isError": false,
    #   "content": [
    #     {
    #       "text": "{\"pages\":[]
    #     }
    #   ]
    # }
    # web_documents = []

    web_documents = json.loads(result.content[0].text).get("pages",[])

    logger.info(f"mcp搜索的结果为:{web_documents}")
    print("---node-web-search-mcp处理结束---")
    add_done_task(state["session_id"], sys._getframe().f_code.co_name, state["is_stream"])
    # 并行的 不要直接返回state
    return {
        "web_search_docs":web_documents
    }


from dotenv import load_dotenv

if __name__ == '__main__':
    load_dotenv()
    test_state = {
        "session_id":"mcp_01",
        "rewritten_query": "HAK 180 在出厂默认状态下，若想在纸张上只把烫金膜转印到顶部 50 mm–170 mm 的局部区域，应在操作面板上如何设置",
        "is_stream":True
    }

    # 调用 websearch_node 函数
    result_state = node_web_search_mcp(test_state)

    # 验证结果
    print("测试结果:")
    print(f"查询内容: {test_state.get('rewritten_query')}")

    # 输出搜索结果
    search_results = result_state.get('web_search_docs', [])
    print(f"搜索结果数量: {len(search_results)}")
    print("search_results", search_results)