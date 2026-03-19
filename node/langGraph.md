# LangGraph

如果说传统的 LangChain Agent 是一个**“黑盒自动驾驶”，那么 LangGraph 就是一套“高精度轨道交通系统”**。它解决了大模型在复杂任务中“容易跑丢、无法人工干预、状态难以持久化”的痛点。

LangGraph 的本质是将 Agent 抽象为一个有向图（Directed Graph）

1. 核心组件 (The Big Three)
   - State (状态)：图的“内存”。通常是一个 TypedDict，记录了对话历史、中间变量等。所有节点共享并修改这个状态。
   - Nodes (节点)：图的“处理单元”。本质上是一个 Python 函数，接收当前 State，处理后返回修改后的 State。
   - Edges (边)：连接节点的路径。
     - 普通边：直接从 A 点到 B 点。
     - 条件边 (Conditional Edges)：根据 LLM 的输出决定下一步去哪里（比如：继续调用工具还是结束任务）。

 2. 关键特性
    - Cycles (循环)：支持 A -> B -> A 的结构，这是实现 ReAct 模式（思考-行动-观察）的基础。    
    - Persistence (持久化)：通过 Checkpointer，你可以随时保存 Agent 的状态。即使程序崩溃，也能从上一步恢复。
    - Human-in-the-loop (人工干预)：支持在特定节点前设置“断点”，等待人类审批。

什么时候该用 LangGraph？

需求场景,是否推荐 LangGraph,原因
简单的单轮问答,❌ 否,直接调用 LLM 即可，Graph 太重。
确定性的线性流程,❌ 否,用 LangChain Chain (LCEL) 更简洁。
需要反复迭代、自纠错的 Agent,✅ 推荐,Graph 的循环能力非常稳健。
需要多人协作、长周期运行的任务,✅ 推荐,Checkpointer 机制无敌。
需要严格合规、人工审批的业务,✅ 推荐,interrupt_before 功能不可替代。