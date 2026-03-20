import os
from dotenv import load_dotenv
from src.rag_storage import ChromaManager
from src.gmail_agent import create_gmail_graph, get_gmail_service
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

def main():
    # 1. 初始化 RAG 向量库
    print("📦 正在初始化知识库...")
    rm = ChromaManager(persist_directory="./chroma_db")
    rm.add_documents_from_directory("./data")
    
    rag_tool = rm.as_tool(
        name="search_policy",
        description="查询公司关于推销邮件的拒绝回复政策")

    # 2. 获取 Gmail 服务并构建 Graph
    print("🤖 正在启动 Agent...")
    service = get_gmail_service()
    app = create_gmail_graph(service, [rag_tool])
    
    # 线程配置 (用于 Checkpointer)
    config = {"configurable": {"thread_id": "audit_001"}, "recursion_limit": 50}
    
    # 3. 运行任务
    query = "看看最新一封邮件，如果是房地产推销，按照政策回复它不需要。"
    inputs = {"messages": [HumanMessage(content=query)]}

    while True:
        # 使用 values 模式获取最新的消息状态
        state = app.get_state(config)
        
        # 如果当前没有在等待（即没有 next 节点），说明需要新输入
        if not state.next:
            for event in app.stream(inputs, config, stream_mode="values"):
                last_msg = event["messages"][-1]
                # 这里只负责打印进度，不处理交互
                if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
                    print(f"🛠️  Agent 准备调用: {[t['name'] for t in last_msg.tool_calls]}")
            inputs = None # 清空输入，准备进入等待状态
        
        # 再次获取状态，检查是否停在了断点
        state = app.get_state(config)
        if state.next and state.next[0] == "tools":
            # 找到 AI 最后的指令
            last_msg = state.values["messages"][-1]
            tool_call = last_msg.tool_calls[0]
            
            if tool_call["name"] == "send_gmail_message":
                print(f"\n📢 [人工审核] 准备发送邮件:")
                print(f"📧 收件人: {tool_call['args'].get('recipient')}")
                print(f"📝 内容: \n{tool_call['args'].get('message')}")
                
                confirm = input("\n❓ 确认发送请按 'y'，修改请直接输入内容，取消请按 'n': ")
                if confirm.lower() == 'n': break
                # 如果用户输入了新内容，可以替换 args (进阶用法)
            
            # 🚀 继续执行
            try:
                app.invoke(None, config)
            except Exception as e:
                if "SSL" in str(e):
                    print("⚠️ 网络抖动 (SSL)，尝试自动重试...")
                    app.invoke(None, config)
                else:
                    raise e
        else:
            break

    print("\n✨ 所有任务处理完毕。")

if __name__ == "__main__":
    main()