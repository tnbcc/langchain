import os
import logging
from pathlib import Path
from typing import Annotated, Sequence, TypedDict, Union
from urllib.parse import urlparse

import httplib2
from dotenv import load_dotenv
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_httplib2 import AuthorizedHttp
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# LangChain & LangGraph
from langchain_community.chat_models import ChatTongyi
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_google_community import GmailToolkit
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

load_dotenv()

# ================= 1. 配置与状态 =================
class AgentState(TypedDict):
    # 使用 add_messages 允许消息自动追加
    messages: Annotated[Sequence[BaseMessage], add_messages]

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
TOKEN_FILE = Path("token.json")
CREDENTIALS_FILE = Path("credentials.json")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= 2. 环境兼容性工具 =================

def get_google_credentials():
    """获取凭证：暂时移除代理以防止 OAuth 握手失败"""
    creds = None
    proxy_keys = ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"]
    proxy_backup = {k: os.environ.pop(k, None) for k in proxy_keys}

    try:
        if TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(GoogleRequest())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
                creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, "w") as token:
                token.write(creds.to_json())
    finally:
        for k, v in proxy_backup.items():
            if v: os.environ[k] = v
    return creds

def get_gmail_tools():
    """构建工具：显式为 httplib2 注入代理"""
    credentials = get_google_credentials()
    proxy_url = os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY')
    
    http_client = httplib2.Http(timeout=60)
    if proxy_url:
        p = urlparse(proxy_url)
        http_client = httplib2.Http(proxy_info=httplib2.ProxyInfo(
            proxy_type=httplib2.socks.PROXY_TYPE_HTTP,
            proxy_host=p.hostname,
            proxy_port=p.port
        ), timeout=60)
    
    service = build('gmail', 'v1', http=AuthorizedHttp(credentials, http=http_client), cache_discovery=False)
    return GmailToolkit(api_resource=service).get_tools()

# ================= 3. LangGraph 核心构建 =================

def create_advanced_gmail_graph():
    tools = get_gmail_tools()
    
    # 初始化 LLM 时避开代理（直连阿里云）
    proxy_keys = ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"]
    proxy_backup = {k: os.environ.pop(k, None) for k in proxy_keys}
    try:
        llm = ChatTongyi(
            model="qwen-max",
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
            temperature=0
        ).bind_tools(tools)
    finally:
        for k, v in proxy_backup.items():
            if v: os.environ[k] = v

    sys_msg = SystemMessage(content=(
        "你是一个 Gmail 自动化专家。执行任务时请：\n"
        "1. 使用 search_gmail_messages 查找最新的一封邮件，获取其 ID。\n"
        "2. 使用 get_gmail_message 仅提取该 ID 对应的邮件内容。\n"
        "3. 仔细判断内容，如果确认是房地产（Real Estate/Property）相关，则调用 send_gmail_message 回复。\n"
        "注意：每次只调用一个工具，等待返回后再进行下一步。"
    ))

    def agent_node(state: AgentState):
        # 节点执行时也需要暂时屏蔽代理访问阿里云
        p_backup = {k: os.environ.pop(k, None) for k in ["https_proxy", "HTTPS_PROXY"]}
        try:
            # 确保消息列表不为空
            response = llm.invoke([sys_msg] + list(state["messages"]))
        finally:
            for k, v in p_backup.items():
                if v: os.environ[k] = v
        return {"messages": [response]}

    # 定义图
    memory = MemorySaver()
    workflow = StateGraph(AgentState)
    
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(tools))

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", tools_condition)
    workflow.add_edge("tools", "agent")

    # 在执行工具前设置断点，用于人工审核发送动作
    return workflow.compile(checkpointer=memory, interrupt_before=["tools"])

# ================= 4. 安全的消息提取与运行 =================

def run_agent(query: str):
    app = create_advanced_gmail_graph()
    thread_config = {"configurable": {"thread_id": "gmail_safe_run_001"}}
    
    print("\n--- 🤖 Agent 启动 ---")
    
    # 初始运行
    inputs = {"messages": [HumanMessage(content=query)]}
    
    # 循环处理流输出，直到遇到断点或结束
    while True:
        stop_for_manual = False
        for event in app.stream(inputs, thread_config, stream_mode="values"):
            # 在 values 模式下，event 直接就是当前最新的 State 字典
            if not event or "messages" not in event:
                continue
                
            last_msg = event["messages"][-1]
            
            # 检查是否有待执行的工具调用
            if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
                for tc in last_msg.tool_calls:
                    if tc["name"] == "send_gmail_message":
                        print(f"\n⚠️  [拦截到发送请求]")
                        print(f"内容摘要: {tc['args'].get('message', '无内容')}")
                        confirm = input("✅ 确认发送请按 'y'，取消请按其他键: ")
                        if confirm.lower() != 'y':
                            print("🚫 任务终止。")
                            return
                        stop_for_manual = True
                    else:
                        print(f"🛠️  准备执行工具: {tc['name']}")

        # 检查是否因为断点停止
        state = app.get_state(thread_config)
        if state.next: # 如果还有下一个节点（即停在了 interrupt_before）
            print(f"⏩ 继续执行后续节点: {state.next}")
            inputs = None # 调用 invoke(None) 恢复执行
            app.invoke(None, thread_config)
        else:
            # 没有下一个节点了，说明运行结束
            if "messages" in state.values:
                print(f"\n✨ 最终回复: {state.values['messages'][-1].content}")
            break

if __name__ == "__main__":
    try:
        run_agent("检查收件箱最新邮件，如果是房地产相关请回复不需要")
    except Exception as e:
        print(f"\n❌ 运行出错: {e}")