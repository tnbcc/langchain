"""
LangGraph Agent 构建器
"""

import os
import sys
from pathlib import Path
from typing import List, Annotated, TypedDict, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dotenv import load_dotenv

load_dotenv()

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_community.chat_models import ChatTongyi

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not DASHSCOPE_API_KEY:
    raise EnvironmentError("请在 .env 文件中配置 DASHSCOPE_API_KEY")


SYSTEM_PROMPT = """你是一个订单查询助手，专门帮助用户查询订单信息。

你可以使用以下工具：
- query_order: 查询单个订单详情，需要输入订单号
- query_order_by_phone: 根据手机号查询订单列表

用户只需要提供订单号或手机号即可查询。
订单号格式示例：ORD20260324001
手机号格式：11位数字

记住用户最近查询过的订单号，方便用户追问。"""


class OrderAgentWithMemory:
    """带记忆的订单查询 Agent"""
    
    def __init__(self, llm_model: str = "qwen-turbo", temperature: float = 0.7):
        from chatBot.tools.order_tool import query_order, query_order_by_phone
        
        self.tools = [query_order, query_order_by_phone]
        self.tool_node = ToolNode(self.tools)
        self.llm = ChatTongyi(model=llm_model, dashscope_api_key=DASHSCOPE_API_KEY, temperature=temperature)
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.store: Dict[str, List[BaseMessage]] = {}
        self._build_graph()
    
    def _build_graph(self):
        class AgentState(TypedDict):
            messages: Annotated[List[BaseMessage], lambda x, y: x + y]
        
        def should_continue(state: AgentState) -> str:
            last_message = state["messages"][-1]
            tool_calls = last_message.additional_kwargs.get("tool_calls", [])
            return "tools" if tool_calls else " END"
        
        def call_model(state: AgentState):
            messages = state["messages"]
            prompt_messages = [("system", SYSTEM_PROMPT)] + messages
            response = self.llm_with_tools.invoke(prompt_messages)
            return {"messages": [response]}
        
        graph = StateGraph(AgentState)
        graph.add_node("agent", call_model)
        graph.add_node("tools", self.tool_node)
        graph.set_entry_point("agent")
        graph.add_conditional_edges("agent", should_continue, {"tools": "tools", " END": END})
        graph.add_edge("tools", "agent")
        
        self.graph = graph.compile()
    
    def get_history(self, session_id: str) -> List[BaseMessage]:
        return self.store.get(session_id, [])
    
    def clear_history(self, session_id: str):
        if session_id in self.store:
            self.store[session_id] = []
    
    def chat(self, message: str, session_id: str = "default") -> str:
        if session_id not in self.store:
            self.store[session_id] = []
        
        history = self.store[session_id]
        
        messages = history + [HumanMessage(content=message)]
        
        result = self.graph.invoke({"messages": messages})
        
        response = result["messages"][-1]
        
        self.store[session_id] = result["messages"]
        
        return response.content


_agent_instance = None

def get_order_agent(llm_model: str = "qwen-turbo", temperature: float = 0.7) -> OrderAgentWithMemory:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = OrderAgentWithMemory(llm_model, temperature)
    return _agent_instance


def build_order_agent(llm_model: str = "qwen-turbo", temperature: float = 0.7):
    """构建订单查询 Agent (兼容旧接口)"""
    return get_order_agent(llm_model, temperature)


def run_order_agent(agent, message: str, session_id: str = "default") -> str:
    """运行订单查询 Agent"""
    if hasattr(agent, 'chat'):
        return agent.chat(message, session_id)
    messages = [HumanMessage(content=message)]
    result = agent.invoke({"messages": messages})
    return result["messages"][-1].content


def is_order_query(message: str) -> bool:
    """判断是否为订单查询"""
    import re
    if re.search(r'ORD\d{8,}', message.upper()):
        return True
    if re.search(r'1[3-9]\d{9}', message):
        return True
    if "订单" in message:
        return True
    return False
