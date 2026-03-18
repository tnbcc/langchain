import os
from dotenv import load_dotenv
from langchain_community.chat_models import ChatTongyi
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from typing import List

load_dotenv()

# 1. 初始化聊天模型（用于对话和摘要生成）
llm = ChatTongyi(
    model="qwen-turbo",
    dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
    temperature=0.7
)

# 2. 自定义摘要记忆类（模拟 ConversationSummaryMemory）
class SummaryChatMessageHistory(BaseChatMessageHistory):
    """基于摘要的记忆，只保留一条系统消息存储对话摘要"""
    def __init__(self, llm, initial_summary: str = ""):
        self.llm = llm
        self.summary = initial_summary
        # 存储原始消息（仅用于摘要更新，不直接用于对话）
        self._raw_messages: List[BaseMessage] = []
        # 暴露给 RunnableWithMessageHistory 的消息列表（仅含摘要系统消息）
        self.messages: List[BaseMessage] = (
            [SystemMessage(content=self.summary)] if self.summary else []
        )

    def add_message(self, message: BaseMessage) -> None:
        """添加一条消息到历史，并在对话结束时更新摘要"""
        self._raw_messages.append(message)
        # 当收到 AI 消息时，表示一轮对话结束，更新摘要
        if isinstance(message, AIMessage):
            self._update_summary()
        # 更新暴露的消息列表为最新的摘要系统消息
        self.messages = [SystemMessage(content=self.summary)] if self.summary else []

    def _update_summary(self) -> None:
        """调用 LLM 根据当前原始消息生成新摘要"""
        if not self._raw_messages:
            return

        # 构建摘要提示
        summary_prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个对话摘要生成器。请将以下对话内容总结为一段简洁的摘要，保留关键信息。"),
            ("human", "{conversation}")
        ])
        # 将原始消息转换为文本格式
        conversation_text = "\n".join([
            f"{'用户' if isinstance(m, HumanMessage) else 'AI'}: {m.content}"
            for m in self._raw_messages
        ])
        # 调用 LLM 生成摘要
        chain = summary_prompt | self.llm
        response = chain.invoke({"conversation": conversation_text})
        self.summary = response.content

    def clear(self) -> None:
        """清空历史"""
        self._raw_messages.clear()
        self.summary = ""
        self.messages = []

# 3. 创建提示模板（包含历史消息占位符）
prompt = ChatPromptTemplate.from_messages([
    ("system", "以下是对话历史摘要：{history}\n请基于此回答用户问题。"),  # 注意：history 将被摘要系统消息填充
    ("human", "{input}")
])

# 4. 构建基础链
chain = prompt | llm

# 5. 记忆存储工厂
store = {}
def get_session_history(session_id: str) -> SummaryChatMessageHistory:
    if session_id not in store:
        store[session_id] = SummaryChatMessageHistory(llm)  # 传入 llm 用于摘要生成
    return store[session_id]

# 6. 包装为带记忆的链
conversation = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history"   # 与模板中的 {history} 对应
)

# 7. 辅助函数：查看当前摘要
def print_summary(session_id: str):
    history = store.get(session_id)
    if history and history.summary:
        print(f"当前摘要: {history.summary}")
    else:
        print("摘要为空")

# 8. 模拟多轮对话
session_id = "user_123"

print("=== 第一轮对话 ===")
response1 = conversation.invoke(
    {"input": "我姐姐明天要过生日，我需要一束生日花束。"},
    config={"configurable": {"session_id": session_id}}
)
print(f"AI: {response1.content}")
print_summary(session_id)

print("\n=== 第二轮对话 ===")
response2 = conversation.invoke(
    {"input": "她喜欢粉色玫瑰，颜色是粉色的。"},
    config={"configurable": {"session_id": session_id}}
)
print(f"AI: {response2.content}")
print_summary(session_id)

print("\n=== 第三轮对话（第二天） ===")
response3 = conversation.invoke(
    {"input": "我又来了，还记得我昨天为什么要来买花吗？"},
    config={"configurable": {"session_id": session_id}}
)
print(f"AI: {response3.content}")
print_summary(session_id)