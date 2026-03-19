import os
import logging
from pathlib import Path
from typing import Annotated, Sequence, TypedDict

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2
from urllib.parse import urlparse

from langchain_community.chat_models import ChatTongyi
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_google_community import GmailToolkit
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

load_dotenv()

# ================= 状态定义 =================
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

# ================= 配置与凭证 =================
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
TOKEN_FILE = Path("token.json")
CREDENTIALS_FILE = Path("credentials.json")

def get_google_credentials():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return creds

# ================= 核心修复：更健壮的工具加载 =================
def get_gmail_tools():
    credentials = get_google_credentials()
    proxy_url = os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY')
    
    # 修复逻辑：显式设置连接池和超时，处理 Chunked 数据
    proxy_info = None
    if proxy_url:
        parsed = urlparse(proxy_url)
        proxy_info = httplib2.ProxyInfo(
            proxy_type=httplib2.socks.PROXY_TYPE_HTTP,
            proxy_host=parsed.hostname,
            proxy_port=parsed.port,
            proxy_user=parsed.username,
            proxy_pass=parsed.password,
        )
    
    # 修复关键点：disable_ssl_certificate_validation 在某些代理环境下是必须的
    # 同时增加 timeout 避免 readline 等待超时变成 None
    http = httplib2.Http(proxy_info=proxy_info, timeout=60) 
    
    authed_http = AuthorizedHttp(credentials, http=http)
    
    # 构建 Gmail 服务时禁用 discovery 缓存，减少额外的网络请求
    service = build('gmail', 'v1', http=authed_http, cache_discovery=False)
    toolkit = GmailToolkit(api_resource=service)
    return toolkit.get_tools()

# ================= 图构建 =================
def create_gmail_graph():
    tools = get_gmail_tools()
    llm = ChatTongyi(
        model="qwen-max",
        dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
        temperature=0
    ).bind_tools(tools)

    # 强化 Prompt：明确要求分步执行，减少单次请求压力
    sys_prompt = SystemMessage(content=(
        "你是一个 Gmail 自动化专家。执行任务时请：\n"
        "1. 使用 search_gmail_messages 查找最新的一封邮件，获取其 ID。\n"
        "2. 使用 get_gmail_message 仅提取该 ID 对应的邮件内容。\n"
        "3. 仔细判断内容，如果确认是房地产（Real Estate/Property）相关，则调用 send_gmail_message 回复。\n"
        "注意：每次只调用一个工具，等待返回后再进行下一步。"
    ))

    def chatbot_node(state: AgentState):
        response = llm.invoke([sys_prompt] + list(state["messages"]))
        return {"messages": [response]}

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", chatbot_node)
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", tools_condition)
    workflow.add_edge("tools", "agent")

    return workflow.compile()

# ================= 执行 =================
def run_agent(task):
    app = create_gmail_graph()
    # 增加 recursion_limit 以应对多次工具往返
    config = {"recursion_limit": 30}
    result = app.invoke({"messages": [HumanMessage(content=task)]}, config=config)
    return result["messages"][-1].content

if __name__ == "__main__":
    try:
        print("🔍 Agent 正在通过代理访问 Gmail...")
        res = run_agent("查一下收件箱里最新一封邮件，提取内容。如果是房地产相关请回复不需要")
        print(f"\n✨ 执行结果:\n{res}")
    except Exception as e:
        logging.exception("有误")
        print(f"❌ 最终拦截到错误: {e}")