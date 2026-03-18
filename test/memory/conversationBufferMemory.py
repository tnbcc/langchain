import os
from dotenv import load_dotenv
from langchain_community.chat_models import ChatTongyi
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory

load_dotenv()

# 1. 初始化聊天模型
llm = ChatTongyi(
    model="qwen-turbo",
    dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
    temperature=0.7
)

# 2. 创建提示模板（保存变量以便最后打印）
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个友好的助手。"),
    MessagesPlaceholder(variable_name="history"),  # 历史消息占位符
    ("human", "{input}")
])

# 3. 构建基础链
chain = prompt | llm

# 4. 内存存储
store = {}
def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

# 5. 包装为带记忆的链
conversation = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history"
)

# 辅助函数：打印当前记忆（类似 conversation.memory.buffer）
def print_memory(session_id: str, prefix=""):
    history = store.get(session_id)
    if history and history.messages:
        buffer = "\n".join([f"{msg.type}: {msg.content}" for msg in history.messages])
        print(f"{prefix}记忆:\n{buffer}")
    else:
        print(f"{prefix}记忆为空")

# 设置会话 ID（可以自定义）
session_id = "user123"

# 第一天的对话
# 回合1
conversation.invoke(
    {"input": "我姐姐明天要过生日，我需要一束生日花束。"},
    config={"configurable": {"session_id": session_id}}
)
print_memory(session_id, "第一次对话后")

# 回合2
conversation.invoke(
    {"input": "她喜欢粉色玫瑰，颜色是粉色的。"},
    config={"configurable": {"session_id": session_id}}
)
print_memory(session_id, "第二次对话后")

# 回合3 （第二天的对话）
conversation.invoke(
    {"input": "我又来了，还记得我昨天为什么要来买花吗？"},
    config={"configurable": {"session_id": session_id}}
)

# 打印提示模板内容（原 conversation.prompt.template）
print("\n提示模板内容:")
print(prompt)  # 打印整个模板对象，包含消息列表
# 如果想以字符串形式查看模板，可以用 prompt.messages 遍历或直接打印

print_memory(session_id, "第三次对话后")