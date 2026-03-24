"""
ChatBot 核心类
"""

import os
import sys
import re
import shutil
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

for var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
    os.environ.pop(var, None)
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

from langchain_community.chat_models import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader, DirectoryLoader, PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables import RunnableLambda

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")


class ChatBot:
    def __init__(
        self,
        knowledge_dir: str,
        persist_directory: str = "./chroma_db",
        embedding_model: str = "text-embedding-v2",
        llm_model: str = "qwen-turbo",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        temperature: float = 0.7,
        top_k: int = 3,
        rebuild: bool = False,
        enable_order_agent: bool = True
    ):
        self.knowledge_dir = knowledge_dir
        self.persist_directory = persist_directory
        self.embedding_model = embedding_model
        self.llm_model = llm_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.temperature = temperature
        self.top_k = top_k
        self.enable_order_agent = enable_order_agent
        
        self._init_components(rebuild)
    
    def _init_components(self, rebuild: bool):
        self.embeddings = DashScopeEmbeddings(model=self.embedding_model)
        self.llm = ChatTongyi(model=self.llm_model, dashscope_api_key=DASHSCOPE_API_KEY, temperature=self.temperature)
        
        if rebuild and os.path.exists(self.persist_directory):
            shutil.rmtree(self.persist_directory)
        os.makedirs(self.persist_directory, exist_ok=True)
        
        self.vectorstore = Chroma(persist_directory=self.persist_directory, embedding_function=self.embeddings)
        
        self._load_knowledge()
        self._build_rag_chain()
        
        if self.enable_order_agent:
            self._build_order_agent()
        
        self.store = {}
    
    def _get_loader(self, file_path: str):
        ext = Path(file_path).suffix.lower()
        if ext == '.pdf':
            return PyPDFLoader(file_path)
        elif ext in ['.docx', '.doc']:
            return Docx2txtLoader(file_path)
        elif ext == '.txt':
            return TextLoader(file_path, encoding='utf-8')
        return None
    
    def _load_knowledge(self):
        if not os.path.exists(self.knowledge_dir) or not os.listdir(self.knowledge_dir):
            print(f"⚠️ 知识库目录为空: {self.knowledge_dir}")
            return
        
        all_docs = []
        supported_exts = ['.pdf', '.docx', '.doc', '.txt']
        
        for root, _, files in os.walk(self.knowledge_dir):
            for file in files:
                file_path = os.path.join(root, file)
                ext = Path(file_path).suffix.lower()
                
                if ext not in supported_exts:
                    continue
                
                loader = self._get_loader(file_path)
                if loader:
                    try:
                        docs = loader.load()
                        all_docs.extend(docs)
                        print(f"📄 已加载: {file}")
                    except Exception as e:
                        print(f"❌ 加载失败 {file}: {e}")
        
        if all_docs:
            splitter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
            splits = splitter.split_documents(all_docs)
            self.vectorstore.add_documents(splits)
            print(f"✅ 已索引 {len(splits)} 个知识片段")
    
    def _build_rag_chain(self):
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": self.top_k})
        
        def get_context(query):
            docs = retriever.invoke(query)
            return "\n\n".join([d.page_content for d in docs])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个公司内部助手，负责帮助员工解答问题。

参考以下公司知识库回答用户问题，如果知识库中没有相关信息，请如实告知用户。

知识库内容：
{context}"""),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])
        
        chain = (
            RunnableLambda(lambda x: {"context": get_context(x["input"]), **x})
            | prompt
            | self.llm
        )
        
        self.chat_chain = RunnableWithMessageHistory(
            chain,
            self.get_session_history,
            input_messages_key="input",
            history_messages_key="history"
        )
    
    def _build_order_agent(self):
        from chatBot.tools.order_agent import build_order_agent, is_order_query as check_order
        self.order_agent = build_order_agent(self.llm_model, self.temperature)
        self._is_order_query = check_order
    
    def get_session_history(self, session_id: str) -> InMemoryChatMessageHistory:
        if session_id not in self.store:
            self.store[session_id] = InMemoryChatMessageHistory()
        return self.store[session_id]
    
    def chat(self, message: str, session_id: str = "default") -> str:
        if self.enable_order_agent and self._is_order_query(message):
            from chatBot.tools.order_agent import run_order_agent
            return run_order_agent(self.order_agent, message, session_id)
        
        config = {"configurable": {"session_id": session_id}}
        response = self.chat_chain.invoke({"input": message}, config=config)
        return response.content
    
    def clear_order_history(self, session_id: str):
        """清除订单查询历史"""
        if hasattr(self.order_agent, 'clear_history'):
            self.order_agent.clear_history(session_id)
    
    def clear_history(self, session_id: str):
        if session_id in self.store:
            self.store[session_id].clear()
    
    def get_history(self, session_id: str) -> List:
        if session_id in self.store:
            return self.store[session_id].messages
        return []
