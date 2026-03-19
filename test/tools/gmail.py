import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from langchain_community.chat_models import ChatTongyi
from langchain_core.messages import HumanMessage
from langchain_google_community import GmailToolkit
from langchain_google_community.gmail.utils import build_gmail_service   
from langchain.agents import create_agent
import httplib2
from urllib.parse import urlparse
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp  

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path                                

load_dotenv()


LOG_FILE = Path("gmail_agent.log")
handler = TimedRotatingFileHandler(LOG_FILE, when="midnight", backupCount=7, encoding='utf-8')
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.basicConfig(level=logging.INFO, handlers=[handler, logging.StreamHandler()])
logger = logging.getLogger(__name__)

# ================= 配置常量 =================
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_FILE = Path("token.json")
CREDENTIALS_FILE = Path("credentials.json")
RECURSION_LIMIT = 10
MODEL_NAME = "qwen-max"
TEMPERATURE = 0.0

def get_google_credentials() -> Credentials:
    """手动获取 Google OAuth 2.0 凭证"""
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"❌ 未找到 {CREDENTIALS_FILE}，请从 Google Cloud Console 下载并放置在当前目录。"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return creds

def get_gmail_tools() -> List:
    """获取 Gmail 工具集（支持代理和自定义超时）"""
    credentials = get_google_credentials()

    # 从环境变量获取代理设置
    proxy_env = os.environ.get('https_proxy') or os.environ.get('http_proxy')
    http = httplib2.Http(timeout=30)

    if proxy_env:
        parsed = urlparse(proxy_env)
        proxy_type = httplib2.socks.PROXY_TYPE_HTTP
        if parsed.scheme == 'socks5':
            proxy_type = httplib2.socks.PROXY_TYPE_SOCKS5
        elif parsed.scheme == 'socks4':
            proxy_type = httplib2.socks.PROXY_TYPE_SOCKS4

        proxy_info = httplib2.ProxyInfo(
            proxy_type=proxy_type,
            proxy_host=parsed.hostname,
            proxy_port=parsed.port,
            proxy_user=parsed.username,
            proxy_pass=parsed.password,
        )
        http = httplib2.Http(proxy_info=proxy_info, timeout=30)
        logger.info(f"使用代理: {parsed.hostname}:{parsed.port}")

    # 使用 AuthorizedHttp 包装 HTTP 对象
    authed_http = AuthorizedHttp(credentials, http=http)

    # 手动构建 Gmail 服务
    service = build('gmail', 'v1', http=authed_http, cache_discovery=False)
    toolkit = GmailToolkit(api_resource=service)
    return toolkit.get_tools()


def run_gmail_agent(user_input: str) -> str:
    """运行 Gmail Agent"""
    llm = ChatTongyi(
        model=MODEL_NAME,
        dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
        temperature=TEMPERATURE,
    )
    tools = get_gmail_tools()
    agent = create_agent(llm, tools)   # 使用新函数名
    print(f"🔍 任务启动: {user_input}\n" + "=" * 50)
    inputs = {"messages": [HumanMessage(content=user_input)]}
    config = {"recursion_limit": RECURSION_LIMIT}
    result = agent.invoke(inputs, config)
    final_message = result["messages"][-1].content
    return final_message

if __name__ == "__main__":
    try:
        task = "帮我查一下收件箱里最新一封邮件，提取关键信息并告诉我。"
        answer = run_gmail_agent(task)
        print("\n✨ Agent 最终执行结果:")
        print(answer)
    except Exception as e:
        logger.exception("Gmail Agent 执行异常")
        print(f"❌ 运行出错: {e}")