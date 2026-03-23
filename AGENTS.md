# Agent Guidelines for LangChain Practice Repository

## Overview
This repository contains LangChain practice code, demos, and learning materials. It focuses on LCEL (LangChain Expression Language), RAG patterns, agent development, and memory management.

---

## Build, Lint, and Test Commands

### Running Tests
```bash
# Run a single test file
python test/memory/conversationBufferMemory.py
python test/react/react.py

# Run any Python file directly
python <path_to_file>
```

### Linting (if configured)
```bash
# Run ruff linter
ruff check .

# Format code with ruff
ruff format .
```

### Virtual Environment
The Python virtual environment is located at `langchain_env/`.
```bash
# Activate the environment
source langchain_env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Code Style Guidelines

### Import Conventions
```python
# Standard library imports first
import os
import json
from typing import List, Optional, TypedDict

# Third-party imports
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# LangChain imports (organized by package)
from langchain_community.chat_models import ChatTongyi
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

# LangChain community/experimental
from langchain_community.agent_toolkits.load_tools import load_tools
```

### Type Hints
- Use `Optional[X]` for nullable types: `Optional[str]`
- Use `List[X]` from typing (not `list[x]`)
- Use `TypedDict` for complex state definitions
- Use `Annotated` with `operator.add` for accumulating state in LangGraph:
```python
from typing import TypedDict, Annotated, List
import operator

class AgentState(TypedDict):
    input: str
    intermediate_steps: Annotated[List[str], operator.add]
    output: str
```

### Pydantic Models
Use Pydantic for structured output and data validation:
```python
from pydantic import BaseModel, Field

class RouteQuery(BaseModel):
    destination: Literal["flower_care", "flower_decoration", "DEFAULT"] = Field(
        description="选择的目标链"
    )
```

### LCEL Patterns

**Basic Chain:**
```python
chain = prompt | llm | parser
```

**Chain with multiple inputs:**
```python
chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | model
    | parser
)
```

**Parallel execution:**
```python
from langchain_core.runnables import RunnableParallel

parallel = RunnableParallel(
    answer=model1 | parser1,
    context=retriever
)
```

**Conditional routing:**
```python
from langchain.schema.runnable import RunnableBranch

branch = RunnableBranch(
    (lambda x: len(x["text"]) < 10, short_text_chain),
    (lambda x: len(x["text"]) < 100, medium_text_chain),
    long_text_chain
)
```

### Memory Patterns

**In-memory chat history:**
```python
store = {}
def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

conversation = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history"
)
```

**Custom memory class:**
```python
class WindowedChatMessageHistory(InMemoryChatMessageHistory):
    def __init__(self, k: int = 3, **kwargs):
        super().__init__(**kwargs)
        self.k = k
    
    def add_messages(self, messages: List[BaseMessage]) -> None:
        super().add_messages(messages)
        self._trim()
```

### Environment Variables
```python
from dotenv import load_dotenv

load_dotenv()

_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not _API_KEY:
    raise EnvironmentError("请检查 .env 文件中的 API Key 配置")
```

### Error Handling
```python
try:
    result = chain.invoke(input)
except Exception as e:
    logger.exception("执行异常")
    print(f"运行出错: {e}")
```

### Logging
```python
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

LOG_FILE = Path("app.log")
handler = TimedRotatingFileHandler(LOG_FILE, when="midnight", backupCount=7)
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.basicConfig(level=logging.INFO, handlers=[handler, logging.StreamHandler()])
logger = logging.getLogger(__name__)
```

### Naming Conventions
- **Classes:** PascalCase (`WindowedChatMessageHistory`)
- **Functions:** snake_case (`get_session_history`)
- **Constants:** UPPER_SNAKE_CASE (`MAX_TOKEN_LIMIT`)
- **Private variables:** prefixed with `_` (`_API_KEY`)
- **Instance variables:** snake_case (`session_id`)

### File Organization
- Test files in `test/` directory with subdirectories for categories:
  - `test/memory/` - Memory pattern examples
  - `test/rag/` - RAG/vector store examples
  - `test/react/` - ReAct agent examples
  - `test/tools/` - Tool integration examples
- Demo applications in `demo/`
- Learning notes in markdown files (Chinese comments for documentation)

### Docstrings
Use docstrings for classes and important functions:
```python
class SummaryChatMessageHistory(BaseChatMessageHistory):
    """基于摘要的记忆，只保留一条系统消息存储对话摘要"""
    def add_message(self, message: BaseMessage) -> None:
        """添加一条消息到历史，并在对话结束时更新摘要"""
        ...
```

### Tool Definition
Use the `@tool` decorator for custom tools:
```python
from langchain.tools import tool

@tool
def calculator(expression: str) -> str:
    """用于计算数学表达式，输入应为数学表达式"""
    try:
        result = numexpr.evaluate(expression)
        return str(result)
    except Exception as e:
        return f"计算错误: {e}"
```

### LangGraph StateGraph Patterns
```python
from langgraph.graph import StateGraph, END

graph = StateGraph(AgentState)
graph.add_node("agent", call_model)
graph.set_entry_point("agent")
graph.add_conditional_edges("agent", should_continue, {"continue": "agent", "end": END})
app = graph.compile()
```

### API Key Validation
Always validate API keys before use:
```python
_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not _API_KEY:
    raise EnvironmentError("请检查 .env 文件中的 API Key 配置")
```

### Comments
- Use Chinese comments for documentation (this codebase is primarily Chinese)
- Use section headers for code organization:
```python
# ================= 环境初始化 =================
# ================= 定义工具 =================
# ================= 构建链 =================
```

---

## Repository Structure
```
langchain/
├── test/
│   ├── memory/          # Memory pattern examples
│   ├── rag/             # RAG examples
│   ├── react/            # ReAct agent examples
│   ├── tools/            # Tool integration examples
│   └── OneFlower/        # Sample documents for testing
├── demo/                # Demo applications
├── node/                # Node-related notes
├── langchain_env/        # Python virtual environment
└── AGENTS.md           # This file
```

---

## Key Dependencies
- `langchain-core`, `langchain-community`
- `langchain-experimental` (for newer features)
- `langgraph` (for agent graphs)
- `pydantic` (for structured output)
- `dashscope` / `ChatTongyi` (for Tongyi LLM)
- `chromadb` (for vector storage)
- `flask` (for web demos)
