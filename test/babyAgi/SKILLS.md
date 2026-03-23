# 鲜花存储策略智能系统

基于 langchain 中 babyAGI 实现，向量数据库用 chroma

## 系统概述

本系统利用 BabyAGI 的目标驱动循环架构，结合向量知识库（Chroma），根据气候变化自动制定鲜花的存储策略。

## BabyAGI 架构

BabyAGI 的核心是一个任务循环：

1. **目标设定** - 确定任务目标（如：根据气候变化制定存储策略）
2. **任务创建** - 根据当前状态和目标创建待执行任务列表
3. **任务执行** - 逐个执行任务，调用知识库获取相关信息
4. **结果评估** - 评估任务执行结果，决定是否继续或结束

## 技术栈

- **LLM**: 通义千问 (Qwen-plus)
- **向量数据库**: Chroma (使用 DashScope Embeddings)
- **框架**: LangChain Core

## 文件结构

```
babyAgi/
├── baby_agi.py      # BabyAGI核心逻辑实现
├── main.py          # 主程序入口
├── data/
│   └── flower_storage.txt  # 鲜花存储知识库
└── chroma_flower/   # Chroma向量数据库存储目录
```

## 运行方式

```bash
cd test/babyAgi
python main.py
```

## 系统流程

```
输入气候信息 → 气候分析 → 创建任务列表 → 循环执行 → 评估结果 → 输出策略
```

## 核心组件

### FlowerStorageBabyAGI 类

- `analyze_climate()`: 分析输入的气候信息
- `create_tasks()`: 根据目标和分析结果创建任务
- `execute_task()`: 执行单个任务
- `evaluate_result()`: 评估任务执行效果
- `get_knowledge_retrieval_tool()`: 获取知识库检索工具
- `run()`: 运行完整的 BabyAGI 循环