import os
import json
import operator
from typing import TypedDict, Annotated, List

import numexpr
from dotenv import load_dotenv
from langchain.tools import tool
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain_community.chat_models import ChatTongyi
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END

load_dotenv()

# ================= 环境变量检查 =================
_API_KEY = os.getenv("DASHSCOPE_API_KEY")
_SERPAPI_KEY = os.getenv("SERPAPI_API_KEY")
if not _API_KEY or not _SERPAPI_KEY:
    raise EnvironmentError("请检查 .env 文件中的 API Key 配置")

# ================= 自定义工具 =================
@tool
def calculator(expression: str) -> str:
    """用于计算数学表达式，输入应为数学表达式，例如 '10 * 1.15' 或 '15% of 100' 但最好是纯数学表达式"""
    try:
        expr = expression.replace('%', '/100')          # 处理百分比
        result = numexpr.evaluate(expr)                  # 安全计算
        return str(result)
    except Exception as e:
        return f"计算错误: {e}"

# ================= 初始化模型和工具 =================
llm = ChatTongyi(
    model="qwen-turbo",
    dashscope_api_key=_API_KEY,
    temperature=0.7
)

serpapi_tools = load_tools(["serpapi"], llm=llm)         # 仅加载搜索工具
tools = serpapi_tools + [calculator]                     # 合并自定义数学工具
tool_dict = {tool.name: tool for tool in tools}

# ================= 定义状态 =================
class AgentState(TypedDict):
    input: str
    chat_history: Annotated[List[str], operator.add]     # 对话历史（可选）
    intermediate_steps: Annotated[List[str], operator.add]  # 中间步骤
    output: str

# ================= 构建提示模板 =================
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个有帮助的助手。你有以下工具可用：\n{tool_descriptions}"),
    ("human", "当前查询：{input}\n之前的步骤：\n{steps}\n\n你必须输出一个 JSON 对象，包含 'action' 和 'action_input' 字段，或者如果已经有最终答案，输出包含 'final_answer' 字段的 JSON 对象。")
])

# ================= Agent 节点函数 =================
def call_model(state: AgentState) -> AgentState:
    """调用 LLM 决定下一步行动或直接返回最终答案"""
    steps = "\n".join(state["intermediate_steps"])
    tool_descriptions = "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])

    # 调用模型
    response = llm.invoke(prompt.format_messages(
        tool_descriptions=tool_descriptions,
        input=state["input"],
        steps=steps
    ))
    content = response.content.strip()

    # 尝试解析 JSON
    try:
        start = content.find('{')
        end = content.rfind('}') + 1
        if start != -1 and end > start:
            json_str = content[start:end]
            result = json.loads(json_str)
        else:
            raise ValueError("未找到 JSON")
    except Exception:
        # 解析失败，将完整输出视为最终答案
        state["output"] = content
        return state

    if "final_answer" in result:
        state["output"] = result["final_answer"]
        return state

    # 否则执行工具调用
    action = result.get("action")
    action_input = result.get("action_input")
    if not action or not action_input:
        state["output"] = content
        return state

    # 记录行动
    state["intermediate_steps"].append(f"Action: {action}, Action Input: {action_input}")

    tool = tool_dict.get(action)
    if tool:
        observation = tool.run(action_input)
    else:
        observation = f"工具 {action} 不存在"

    state["intermediate_steps"].append(f"Observation: {observation}")
    return state

# ================= 条件判断 =================
def should_continue(state: AgentState) -> str:
    """决定是否继续循环"""
    return "end" if state.get("output") else "continue"

# ================= 构建图 =================
graph = StateGraph(AgentState)
graph.add_node("agent", call_model)
graph.set_entry_point("agent")
graph.add_conditional_edges("agent", should_continue, {"continue": "agent", "end": END})
app = graph.compile()

# ================= 运行 Agent =================
if __name__ == "__main__":
    initial_state = {
        "input": "目前市场上玫瑰花的平均价格是多少？如果我在此基础上加价15%卖出，应该如何定价？",
        "chat_history": [],
        "intermediate_steps": [],
        "output": ""
    }
    final_state = app.invoke(initial_state)
    print(final_state["output"])