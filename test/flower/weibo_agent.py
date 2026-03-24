"""
微博鲜花推广大V搜寻Agent
帮助市场营销部门找到适合做鲜花推广的大V
"""

import os
from typing import List, Any, Dict
from dotenv import load_dotenv

load_dotenv()

_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not _API_KEY:
    raise EnvironmentError("请检查 .env 文件中的 API Key 配置")

from langchain_community.chat_models import ChatTongyi
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool, Tool
from langchain_core.agents import AgentFinish
from langchain.agents import create_agent

from weibo_search import create_weibo_search_tools
from weibo_crawler import create_weibo_crawler_tools


SYSTEM_PROMPT = """你是一个专业的微博营销专家，帮助市场营销部门找到适合鲜花推广的大V。

你有以下工具可用：
1. search_weibo_influencers: 搜索微博上有影响力的鲜花相关博主
2. get_uid_by_username: 根据用户名获取UID
3. get_weibo_user_info: 根据UID获取用户完整信息（JSON）
4. get_weibo_user_report: 获取用户完整报告（含分析和建议）
5. get_user_tweets: 获取用户最近的微博帖子

工作流程：
1. 首先使用search_weibo_influencers搜索相关领域的博主
2. 根据返回的UID获取详细用户信息
3. 生成联络方案

请按步骤执行，帮助用户找到最合适的大V合作对象。"""


class WeiboFlowerPromotionAgent:
    """微博鲜花推广大V搜寻Agent"""

    def __init__(self):
        self.model = ChatTongyi(model="qwen-plus", temperature=0.7)

        search_tools = create_weibo_search_tools()
        crawler_tools = create_weibo_crawler_tools()

        self.all_tools: List[Tool] = search_tools + crawler_tools

        self.agent = create_agent(
            model=self.model,
            tools=self.all_tools,
            system_prompt=SYSTEM_PROMPT
        )

    def run(self, task: str, max_steps: int = 10) -> str:
        """运行Agent"""
        print("\n" + "=" * 60)
        print("🔍 微博鲜花推广大V搜寻系统")
        print("=" * 60)

        state = {"input": task, "agent_scratchpad": []}
        step = 0

        while step < max_steps:
            step += 1
            print(f"\n--- 步骤 {step} ---")

            result = self.agent.invoke(state)

            if isinstance(result, AgentFinish):
                return result.return_values["output"]

            if isinstance(result, dict):
                action = result.get("actions", [{}])[0] if result.get("actions") else {}
                print(f"执行工具: {action.get('tool', 'unknown')}")
                print(f"工具输入: {action.get('tool_input', {})}")

                tool_result = result.get("steps", [{}])[0].get("observations", "")
                print(f"工具结果: {str(tool_result)[:200]}...")

                state["agent_scratchpad"].append({
                    "action": action,
                    "observation": tool_result
                })
            else:
                print(f"结果类型: {type(result)}")
                print(f"结果: {str(result)[:200]}")

        return "执行超时"


def run_demo():
    """演示模式"""
    agent = WeiboFlowerPromotionAgent()

    tasks = [
        "搜索喜欢玫瑰花的微博大V，找到他们的UID",
        "找到专注园艺和鲜花的微博博主，返回他们的详细信息",
        "搜索花卉领域的意见领袖，评估他们是否适合做鲜花产品推广"
    ]

    print("\n" + "=" * 70)
    print("🌸 微博鲜花推广大V搜寻系统 - Demo")
    print("=" * 70)
    print("\n可执行任务示例：")
    for i, task in enumerate(tasks, 1):
        print(f"  {i}. {task}")

    print("\n" + "-" * 70)
    user_task = input("\n请输入您的任务（或直接回车使用默认任务）: ").strip()

    if not user_task:
        user_task = tasks[0]

    print(f"\n📝 执行任务: {user_task}")
    result = agent.run(user_task)

    print("\n" + "=" * 70)
    print("📊 执行结果:")
    print("=" * 70)
    print(result)


def single_task_mode(keywords: str = "玫瑰花 鲜花"):
    """单任务模式"""
    agent = WeiboFlowerPromotionAgent()

    task = f"搜索喜欢{keywords}的微博大V，返回UID和个人信息"

    result = agent.run(task)

    print("\n" + "=" * 70)
    print("📊 最终结果:")
    print("=" * 70)
    print(result)

    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        keywords = " ".join(sys.argv[1:])
        single_task_mode(keywords)
    else:
        run_demo()