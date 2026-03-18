"""
LangChain LCEL + ChatTongyi + 自定义滑动窗口记忆
"""

import os
from typing import List
from dotenv import load_dotenv

from langchain_community.chat_models import ChatTongyi
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

# ─────────────────────────────────────────────
# 0. 环境初始化 & 提前校验
# ─────────────────────────────────────────────
load_dotenv()

_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not _API_KEY:
    raise EnvironmentError(
        "❌ 未找到 DASHSCOPE_API_KEY，请在 .env 文件中配置。"
    )

# ─────────────────────────────────────────────
# 1. 自定义滑动窗口消息历史（修复版）
# ─────────────────────────────────────────────
class WindowedChatMessageHistory(InMemoryChatMessageHistory):
    """
    滑动窗口消息历史容器。
    继承自官方的 InMemoryChatMessageHistory，增加滑动窗口裁剪机制。
    """
    # 显式声明类型供 Pydantic 解析，但在 __init__ 中赋值
    k: int = 3

    def __init__(self, k: int = 3, **kwargs):
        # 显式调用父类初始化，并接收自定义参数，兼容所有 Pydantic 版本
        super().__init__(**kwargs)
        self.k = k

    @property
    def _max_messages(self) -> int:
        """窗口最大消息条数（每轮 = Human + AI = 2条）"""
        return self.k * 2

    def _trim(self) -> None:
        """裁剪历史，仅保留最近 k 轮消息"""
        if len(self.messages) > self._max_messages:
            self.messages = self.messages[-self._max_messages :]

    # ⚠️ 必须重写 add_messages（复数），因为最新版 LangChain 底层通常调用这个方法
    def add_messages(self, messages: List[BaseMessage]) -> None:
        """批量添加消息，并自动触发窗口裁剪"""
        super().add_messages(messages)
        self._trim()

    def add_message(self, message: BaseMessage) -> None:
        """单条添加消息，并自动触发窗口裁剪"""
        super().add_message(message)
        self._trim()

# ─────────────────────────────────────────────
# 2. 会话存储管理器
# ─────────────────────────────────────────────
class SessionStore:
    def __init__(self, default_k: int = 3) -> None:
        self.default_k = default_k
        self._store: dict[str, WindowedChatMessageHistory] = {}

    def get(self, session_id: str) -> WindowedChatMessageHistory:
        if session_id not in self._store:
            # 现在这里传参 k=self.default_k 就绝对不会报错了
            self._store[session_id] = WindowedChatMessageHistory(k=self.default_k)
        return self._store[session_id]

    def list_sessions(self) -> list[str]:
        return list(self._store.keys())

    def print_memory(self, session_id: str, label: str = "") -> None:
        history = self._store.get(session_id)
        tag = f"[{label}] " if label else ""

        if not history or not history.messages:
            print(f"  {tag}🧠 记忆窗口为空")
            return

        print(f"\n  {tag}🧠 记忆窗口（k={history.k}，当前 {len(history.messages)} 条）：")
        print("  " + "─" * 52)
        for msg in history.messages:
            if isinstance(msg, HumanMessage):
                icon, role = "🧑", "Human"
            elif isinstance(msg, AIMessage):
                icon, role = "🤖", "AI   "
            else:
                icon, role = "❓", msg.type

            content = msg.content
            preview = content[:80] + ("..." if len(content) > 80 else "")
            print(f"  {icon} {role}: {preview}")
        print("  " + "─" * 52)


# ─────────────────────────────────────────────
# 3. 初始化模型 & Prompt & Chain
# ─────────────────────────────────────────────
llm = ChatTongyi(
    model="qwen-turbo",
    dashscope_api_key=_API_KEY,
    temperature=0.7,
)

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "你是一家花店的专业助手，擅长根据顾客需求推荐花束。"
        "请根据对话历史提供个性化建议，回答简洁友好。"
    ),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}"),
])

chain = prompt | llm

# 统一配置窗口大小为 1（保留最近 1 轮）
session_store = SessionStore(default_k=1)

conversation = RunnableWithMessageHistory(
    chain,
    session_store.get,
    input_messages_key="input",
    history_messages_key="history",
)

# ─────────────────────────────────────────────
# 4. 交互函数与主程序
# ─────────────────────────────────────────────
def chat(user_input: str, session_id: str, label: str = "") -> str:
    response = conversation.invoke(
        {"input": user_input},
        config={"configurable": {"session_id": session_id}},
    )
    session_store.print_memory(session_id, label=label)
    return response.content

def main() -> None:
    SESSION = "user_alice"

    print("=" * 60)
    print("🌸 花店智能助手 × 滑动窗口对话记忆 Demo")
    print(f"   窗口大小 k={session_store.default_k}（保留最近 {session_store.default_k} 轮对话）")
    print("=" * 60)

    print("\n📅 第一天\n")

    print("🧑 Round 1：我姐姐明天要过生日，我需要一束生日花束。")
    reply1 = chat("我姐姐明天要过生日，我需要一束生日花束。", SESSION, label="Round 1 后")
    print(f"🤖 AI: {reply1}\n")

    print("🧑 Round 2：她喜欢粉色玫瑰，颜色是粉色的。")
    reply2 = chat("她喜欢粉色玫瑰，颜色是粉色的。", SESSION, label="Round 2 后")
    print(f"🤖 AI: {reply2}\n")

    print("\n📅 第二天（同一会话继续）\n")

    print("🧑 Round 3：我又来了，还记得我昨天为什么要来买花吗？")
    reply3 = chat("我又来了，还记得我昨天为什么要来买花吗？", SESSION, label="Round 3 后")
    print(f"🤖 AI: {reply3}\n")


if __name__ == "__main__":
    main()
