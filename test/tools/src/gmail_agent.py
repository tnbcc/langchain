import os
from pathlib import Path
from typing import Annotated, Sequence, TypedDict
from urllib.parse import urlparse
import httplib2

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import google_auth_httplib2

from langchain_community.chat_models import ChatTongyi
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_google_community import GmailToolkit
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain.tools import tool
import base64

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


import os
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import google_auth_httplib2

def get_gmail_service():
    SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
    token_path = Path("token.json")
    creds = None
    
    # 代理控制
    p_keys = ["https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY"]

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    
    if not creds or not creds.valid:
        p_backup = {k: os.environ.pop(k, None) for k in p_keys}
        try:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, "w") as token:
                token.write(creds.to_json())
        finally:
            for k, v in p_backup.items():
                if v: os.environ[k] = v

    return build('gmail', 'v1', credentials=creds, cache_discovery=False)

@tool
def robust_get_gmail_content(message_id: str):
    """根据邮件 ID 获取邮件正文。请务必使用 search_gmail 返回的真实 ID。"""
    # 这里直接闭包使用 global 或传入的 service
    try:
        # 使用 format='full' 避免 metadata 模式下数据缺失
        # .execute() 内部在 Python 3.12 下比 LangChain 封装的 run() 更稳定
        msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()
        
        payload = msg.get('payload', {})
        snippet = msg.get('snippet', '')
        
        # 递归查找 text/plain 部分
        def find_body(parts):
            for part in parts:
                if part.get('mimeType') == 'text/plain':
                    return part.get('body', {}).get('data', '')
                if 'parts' in part:
                    res = find_body(part['parts'])
                    if res: return res
            return ''

        data = find_body(payload.get('parts', [])) or payload.get('body', {}).get('data', '')
        if data:
            body = base64.urlsafe_b64decode(data).decode('utf-8')
        else:
            body = f"(正文较复杂，预览内容：{snippet})"
            
        return f"邮件内容如下：\n{body[:1500]}"
    except Exception as e:
        return f"获取邮件失败，错误详情: {str(e)}"


def create_gmail_graph(service_obj, extra_tools=[]):
    """构建 LangGraph"""
    # 1. 获取官方工具包
    toolkit = GmailToolkit(api_resource=service_obj)
    raw_tools = toolkit.get_tools()
    
    # 2. 🚀 关键过滤：排除掉官方那个会报 NoneType 错误的 get_gmail_message
    # 我们只保留 search, send 等工具，用我们的 robust_get_gmail_content 替换获取功能
    safe_tools = [
        t for t in raw_tools 
        if t.name not in ["get_gmail_message", "get_gmail_thread"]
    ]
    
    # 3. 合并自定义工具
    # 将 robust_get_gmail_content 加入列表
    all_tools = safe_tools + [robust_get_gmail_content] + extra_tools

    # --- 以下 LLM 初始化部分保持不变 ---
    p_keys = ["https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY"]
    p_old = {k: os.environ.pop(k, None) for k in p_keys}
    llm = ChatTongyi(model="qwen-max", temperature=0).bind_tools(all_tools)
    for k, v in p_old.items(): 
        if v: os.environ[k] = v

    def chatbot(state: AgentState):
        sys_msg = SystemMessage(content=(
            "你是一个邮件助理。请先用 search_gmail 搜索，"
            "然后使用 robust_get_gmail_content 读取内容。" # 引导 LLM 使用新工具
        ))
        p_tmp = {k: os.environ.pop(k, None) for k in p_keys}
        try:
            response = llm.invoke([sys_msg] + list(state["messages"]))
        finally:
            for k, v in p_tmp.items():
                if v: os.environ[k] = v
        return {"messages": [response]}

    # Graph 结构保持不变
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", chatbot)
    workflow.add_node("tools", ToolNode(all_tools))
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", tools_condition)
    workflow.add_edge("tools", "agent")

    return workflow.compile(checkpointer=MemorySaver(), interrupt_before=["tools"])