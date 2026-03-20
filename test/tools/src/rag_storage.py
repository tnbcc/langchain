import os
from langchain_chroma import Chroma  
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.tools import Tool

class ChromaManager:
    def __init__(self, persist_directory="./chroma_db", model_name="text-embedding-v2"):
        self.persist_directory = persist_directory
        self.model_name = model_name
        
        # 🛡️ 临时清除代理，防止初始化时连接阿里云失败
        p_keys = ["https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY", "all_proxy", "ALL_PROXY"]
        p_backup = {k: os.environ.pop(k, None) for k in p_keys}
        
        try:
            self.embeddings = DashScopeEmbeddings(model=self.model_name)
            if not os.path.exists(self.persist_directory):
                os.makedirs(self.persist_directory)
            self.vectorstore = Chroma(
                persist_directory=self.persist_directory, 
                embedding_function=self.embeddings
            )
        finally:
            # 恢复代理，供 Gmail 使用
            for k, v in p_backup.items():
                if v: os.environ[k] = v

    def add_documents_from_directory(self, dir_path="./data"):
        """扫描目录并更新向量库"""
        if not os.path.exists(dir_path) or not os.listdir(dir_path):
            print(f"📁 目录 {dir_path} 为空或不存在，跳过索引。")
            return

        # 🛡️ 同样在处理文档 Embedding 时屏蔽代理
        p_keys = ["https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY"]
        p_backup = {k: os.environ.pop(k, None) for k in p_keys}
        
        try:
            loader = DirectoryLoader(dir_path, glob="*.txt", loader_cls=TextLoader)
            documents = loader.load()
            splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=60)
            docs = splitter.split_documents(documents)
            
            if docs:
                self.vectorstore.add_documents(docs)
                print(f"✅ 已成功索引 {len(docs)} 个知识片段")
        finally:
            for k, v in p_backup.items():
                if v: os.environ[k] = v

    def as_tool(self, name="search_policy", description="查询公司关于推销邮件的回复政策"):
        """导出为 Agent 工具，并内置代理屏蔽逻辑"""
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})
        
        def safe_retriever(query: str):
            # 🛡️ 在检索时临时关掉代理，防止 DashScope 报错
            p_keys = ["https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY"]
            p_backup = {k: os.environ.pop(k, None) for k in p_keys}
            try:
                # 执行实际检索（触发 Embedding 计算）
                docs = retriever.invoke(query)
                return "\n\n".join([d.page_content for d in docs])
            finally:
                for k, v in p_backup.items():
                    if v: os.environ[k] = v

        return Tool(
            name=name,
            description=description,
            func=safe_retriever
        )