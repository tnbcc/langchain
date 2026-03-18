import os
from dotenv import load_dotenv
from langchain_community.chat_models import ChatTongyi
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from typing import List, Optional

load_dotenv()

# 环境初始化
_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not _API_KEY:
    raise EnvironmentError("❌ 未找到 DASHSCOPE_API_KEY，请在 .env 文件中配置。")

llm = ChatTongyi(
    model="qwen-turbo",
    dashscope_api_key=_API_KEY,
    temperature=0.7,
)

# 预定义摘要生成和合并的提示模板（复用）
SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是一个对话摘要生成器。请将以下对话内容总结为一段简洁的摘要。"),
    ("human", "{conversation}")
])

MERGE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是一个对话摘要合并器。请将旧的摘要和新的对话内容合并为一个更全面的新摘要。"),
    ("human", "旧摘要：{old_summary}\n新对话：{new_conversation}")
])

class SummaryBufferChatMessageHistory(BaseChatMessageHistory):
    """
    基于摘要和缓冲区的记忆管理。
    - 保留最近的消息（缓冲区）和一个历史摘要。
    - 当总 token 数超过 max_token_limit 时，将最早的消息合并到摘要中。
    """
    def __init__(self, llm, max_token_limit: int):
        self.llm = llm
        self.max_token_limit = max_token_limit
        self._summary: Optional[str] = None
        self._recent_messages: List[BaseMessage] = []

        # 构建摘要生成链（可复用）
        self._summary_chain = SUMMARY_PROMPT | llm
        self._merge_chain = MERGE_PROMPT | llm

    @property
    def messages(self) -> List[BaseMessage]:
        """返回最终传递给模型的消息列表"""
        result = []
        if self._summary:
            result.append(SystemMessage(content=f"对话历史摘要：{self._summary}"))
        result.extend(self._recent_messages)
        return result

    def add_message(self, message: BaseMessage) -> None:
        self._recent_messages.append(message)
        self._compress_if_needed()

    def _total_tokens(self) -> int:
        total = 0
        if self._summary:
            total += self.llm.get_num_tokens(self._summary)
        for msg in self._recent_messages:
            total += self.llm.get_num_tokens(msg.content)
        return total

    def _compress_if_needed(self) -> None:
        while self._total_tokens() > self.max_token_limit:
            self._compress_earliest()

    def _compress_earliest(self) -> None:
        if len(self._recent_messages) < 2:
            self._recent_messages.clear()
            return

        # 取出最早的一对 human+AI 消息
        msg1 = self._recent_messages.pop(0)
        msg2 = self._recent_messages.pop(0)
        conversation_text = f"用户：{msg1.content}\nAI：{msg2.content}"

        # 生成新摘要或合并
        if self._summary is None:
            new_summary = self._summary_chain.invoke({"conversation": conversation_text}).content
            self._summary = new_summary
        else:
            new_summary = self._merge_chain.invoke({
                "old_summary": self._summary,
                "new_conversation": conversation_text
            }).content
            self._summary = new_summary

    def clear(self) -> None:
        self._summary = None
        self._recent_messages.clear()

# 构建 LCEL 链
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个友好的助手。"),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])

chain = prompt | llm

# 记忆存储
store = {}
def get_session_history(session_id: str) -> SummaryBufferChatMessageHistory:
    if session_id not in store:
        store[session_id] = SummaryBufferChatMessageHistory(llm, max_token_limit=300)
    return store[session_id]

conversation = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history"
)

# 模拟对话
session_id = "user_123"

response = conversation.invoke(
    {"input": "我姐姐明天要过生日，我需要一束生日花束。"},
    config={"configurable": {"session_id": session_id}}
)
print(response.content)

response = conversation.invoke(
    {"input": "她喜欢粉色玫瑰，颜色是粉色的。"},
    config={"configurable": {"session_id": session_id}}
)
print(response.content)

response = conversation.invoke(
    {"input": "我又来了，还记得我昨天为什么要来买花吗？"},
    config={"configurable": {"session_id": session_id}}
)
print(response.content)