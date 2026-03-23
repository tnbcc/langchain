"""
BabyAGI 鲜花存储策略系统
核心功能：任务自动创建、优先级排序和执行
向量数据库：Chroma
"""

import os
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not _API_KEY:
    raise EnvironmentError("请检查 .env 文件中的 API Key 配置")

from langchain_community.chat_models import ChatTongyi
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, CommaSeparatedListOutputParser
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


class Task:
    """任务对象"""
    def __init__(self, task_id: int, task_name: str):
        self.task_id = task_id
        self.task_name = task_name
        self.status = "pending"
        self.result = ""

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "status": self.status,
            "result": self.result
        }


# ================= Chroma任务存储 =================

class ChromaTaskStore:
    """使用Chroma向量数据库存储和管理任务"""

    def __init__(self, persist_directory: str = "./chroma_tasks"):
        self._init_embeddings()
        if not os.path.exists(persist_directory):
            os.makedirs(persist_directory)
        self.vectorstore = Chroma(
            persist_directory=persist_directory,
            embedding_function=self.embeddings
        )
        self.task_counter = self._get_max_task_id() + 1

    def _init_embeddings(self):
        p_keys = ["https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY", "all_proxy", "ALL_PROXY"]
        p_backup = {k: os.environ.pop(k, None) for k in p_keys}
        try:
            self.embeddings = DashScopeEmbeddings(model="text-embedding-v2")
        finally:
            for k, v in p_backup.items():
                if v: os.environ[k] = v

    def _get_max_task_id(self) -> int:
        try:
            docs = self.vectorstore.get(limit=1000)
            if docs["ids"]:
                ids = [int(d.replace("task_", "")) for d in docs["ids"] if d.startswith("task_")]
                return max(ids) if ids else 0
        except: pass
        return 0

    def add_task(self, task_name: str) -> int:
        """添加新任务"""
        task_id = self.task_counter
        self.task_counter += 1

        doc = Document(
            page_content=task_name,
            metadata={"task_id": task_id, "status": "pending", "result": ""}
        )

        p_keys = ["https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY", "all_proxy", "ALL_PROXY"]
        p_backup = {k: os.environ.pop(k, None) for k in p_keys}
        try:
            self.vectorstore.add_documents([doc], ids=[f"task_{task_id}"])
        finally:
            for k, v in p_backup.items():
                if v: os.environ[k] = v

        return task_id

    def get_task(self, task_id: int) -> Optional[Dict]:
        """根据ID获取任务"""
        p_keys = ["https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY", "all_proxy", "ALL_PROXY"]
        p_backup = {k: os.environ.pop(k, None) for k in p_keys}
        try:
            docs = self.vectorstore.get(ids=[f"task_{task_id}"])
            if docs["documents"]:
                m = docs["metadatas"][0]
                return {"task_id": m["task_id"], "task_name": docs["documents"][0], "status": m["status"], "result": m.get("result", "")}
        except: pass
        finally:
            for k, v in p_backup.items():
                if v: os.environ[k] = v
        return None

    def update_task(self, task_id: int, status: str, result: str = ""):
        """更新任务状态和结果"""
        p_keys = ["https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY", "all_proxy", "ALL_PROXY"]
        p_backup = {k: os.environ.pop(k, None) for k in p_keys}
        try:
            docs = self.vectorstore.get(ids=[f"task_{task_id}"])
            if docs["documents"]:
                self.vectorstore.delete(ids=[f"task_{task_id}"])
                self.vectorstore.add_documents([
                    Document(page_content=docs["documents"][0], metadata={"task_id": task_id, "status": status, "result": result})
                ], ids=[f"task_{task_id}"])
        except Exception as e:
            print(f"更新任务失败: {e}")
        finally:
            for k, v in p_backup.items():
                if v: os.environ[k] = v

    def get_pending_tasks(self) -> List[Dict]:
        """获取所有待办任务"""
        results = []
        p_keys = ["https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY", "all_proxy", "ALL_PROXY"]
        p_backup = {k: os.environ.pop(k, None) for k in p_keys}
        try:
            docs = self.vectorstore.get(limit=1000)
            for i, doc in enumerate(docs["documents"]):
                m = docs["metadatas"][i]
                if m["status"] == "pending":
                    results.append({"task_id": m["task_id"], "task_name": doc, "status": m["status"]})
        except: pass
        finally:
            for k, v in p_backup.items():
                if v: os.environ[k] = v
        return results

    def get_completed_tasks(self) -> List[Dict]:
        """获取已完成任务"""
        results = []
        p_keys = ["https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY", "all_proxy", "ALL_PROXY"]
        p_backup = {k: os.environ.pop(k, None) for k in p_keys}
        try:
            docs = self.vectorstore.get(limit=1000)
            for i, doc in enumerate(docs["documents"]):
                m = docs["metadatas"][i]
                if m["status"] == "completed":
                    results.append({"task_id": m["task_id"], "task_name": doc, "status": m["status"], "result": m.get("result", "")})
        except: pass
        finally:
            for k, v in p_backup.items():
                if v: os.environ[k] = v
        return results


# ================= 功能函数 =================

def get_next_task(task_store: ChromaTaskStore) -> Optional[Dict]:
    """获取下一个待执行任务"""
    pending = task_store.get_pending_tasks()
    if pending:
        return pending[0]
    return None


def prioritize_tasks(model, task_store: ChromaTaskStore, knowledge_vectorstore: Chroma) -> List[int]:
    """任务优先级排序链 - 根据相关性和重要性排序"""
    pending_tasks = task_store.get_pending_tasks()
    if not pending_tasks:
        return []

    p_keys = ["https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY", "all_proxy", "ALL_PROXY"]
    p_backup = {k: os.environ.pop(k, None) for k in p_keys}

    try:
        tasks_text = "\n".join([f"[{t['task_id']}] {t['task_name']}" for t in pending_tasks])

        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个任务优先级专家。根据任务的重要性和紧迫性对任务排序。
考虑因素：
1. 任务是否为核心目标服务
2. 任务是否有依赖关系
3. 任务的紧迫程度

请按执行顺序返回任务ID列表，用逗号分隔，如：1,3,2"""),
            ("user", f"待排序任务：\n{tasks_text}")
        ])

        chain = prompt | model | StrOutputParser()
        result = chain.invoke({})

        task_ids = [int(t.strip()) for t in result.split(",") if t.strip().isdigit()]
        return task_ids if task_ids else [t["task_id"] for t in pending_tasks]
    except Exception as e:
        print(f"优先级排序失败: {e}")
        return [t["task_id"] for t in pending_tasks]
    finally:
        for k, v in p_backup.items():
            if v: os.environ[k] = v


def _get_top_tasks(task_store: ChromaTaskStore, prioritized_ids: List[int], top_n: int = 5) -> List[Dict]:
    """获取优先级最高的任务列表"""
    all_pending = task_store.get_pending_tasks()
    id_to_task = {t["task_id"]: t for t in all_pending}

    top_tasks = []
    for tid in prioritized_ids:
        if tid in id_to_task:
            top_tasks.append(id_to_task[tid])
            if len(top_tasks) >= top_n:
                break

    if len(top_tasks) < top_n:
        for t in all_pending:
            if t not in top_tasks and len(top_tasks) < top_n:
                top_tasks.append(t)

    return top_tasks


def execute_task(model, task: Dict, task_store: ChromaTaskStore, knowledge_vectorstore: Chroma) -> str:
    """执行单个任务"""
    task_id = task["task_id"]
    task_name = task["task_name"]

    p_keys = ["https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY", "all_proxy", "ALL_PROXY"]
    p_backup = {k: os.environ.pop(k, None) for k in p_keys}

    try:
        retriever = knowledge_vectorstore.as_retriever(search_kwargs={"k": 4})
        context_docs = retriever.invoke(task_name)
        context = "\n\n".join([d.page_content for d in context_docs])

        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的鲜花存储策略专家。根据任务要求，结合知识库内容，
生成具体的执行方案。请确保策略具体、可操作。

知识库包含各种鲜花的最适存储条件、不同气候应对策略等信息。"""),
            ("user", f"任务：{task_name}\n\n相关知识：{context}")
        ])

        chain = prompt | model | StrOutputParser()
        result = chain.invoke({})

        task_store.update_task(task_id, "completed", result)
        return result
    except Exception as e:
        print(f"执行任务失败: {e}")
        task_store.update_task(task_id, "failed", str(e))
        return f"执行失败: {e}"
    finally:
        for k, v in p_backup.items():
            if v: os.environ[k] = v


# ================= BabyAGI 主类 =================

class BabyAGI:
    """BabyAGI主类 - 控制整个系统运行流程"""

    def __init__(self, objective: str, data_dir: str = "./data"):
        self.objective = objective
        self.model = ChatTongyi(model="qwen-plus", temperature=0.7)
        self.task_store = ChromaTaskStore(persist_directory="./chroma_tasks")
        self.knowledge_vectorstore = self._init_knowledge_base(data_dir)
        self.task_creation_chain = self._build_task_creation_chain()
        self.execution_results = []

    def _init_knowledge_base(self, data_dir: str) -> Chroma:
        """初始化鲜花知识库"""
        p_keys = ["https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY", "all_proxy", "ALL_PROXY"]
        p_backup = {k: os.environ.pop(k, None) for k in p_keys}

        try:
            embeddings = DashScopeEmbeddings(model="text-embedding-v2")
            persist_dir = "./chroma_flower"
            if not os.path.exists(persist_dir):
                os.makedirs(persist_dir)

            vectorstore = Chroma(persist_directory=persist_dir, embedding_function=embeddings)

            if vectorstore._collection.count() == 0:
                self._load_documents(data_dir, vectorstore)

            return vectorstore
        finally:
            for k, v in p_backup.items():
                if v: os.environ[k] = v

    def _load_documents(self, data_dir: str, vectorstore: Chroma):
        """加载鲜花存储知识到向量库"""
        if not os.path.exists(data_dir) or not os.listdir(data_dir):
            print(f"📁 知识库目录为空")
            return

        p_keys = ["https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY"]
        p_backup = {k: os.environ.pop(k, None) for k in p_keys}

        try:
            loader = TextLoader(f"{data_dir}/flower_storage.txt")
            documents = loader.load()
            splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
            docs = splitter.split_documents(documents)

            if docs:
                vectorstore.add_documents(docs)
                print(f"✅ 已索引 {len(docs)} 个知识片段")
        finally:
            for k, v in p_backup.items():
                if v: os.environ[k] = v

    def _build_task_creation_chain(self):
        """定义任务创建链 - 根据完成的任务生成新任务"""
        p_keys = ["https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY", "all_proxy", "ALL_PROXY"]
        p_backup = {k: os.environ.pop(k, None) for k in p_keys}

        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", """你是一个任务规划专家。根据已完成的任务和结果，判断目标是否达成。
如果没有完全达成，则生成新的子任务来完成目标。

规则：
1. 如果目标已完全达成，返回空列表
2. 如果目标未完成，生成1-3个更具体的子任务
3. 任务要具体、可执行
4. 每个任务单独一行，不要编号"""),
                ("user", "目标：{objective}\n最近完成的任务：{last_task}\n任务结果：{result}")
            ])

            return prompt | self.model | StrOutputParser()
        finally:
            for k, v in p_backup.items():
                if v: os.environ[k] = v

    def add_initial_task(self, task_name: str):
        """添加初始任务"""
        task_id = self.task_store.add_task(task_name)
        print(f"📋 添加初始任务 [{task_id}]: {task_name}")
        return task_id

    def print_task_list(self):
        """输出任务列表"""
        print("\n" + "=" * 60)
        print("📋 当前任务列表")
        print("=" * 60)

        pending = self.task_store.get_pending_tasks()
        completed = self.task_store.get_completed_tasks()

        print(f"\n⏳ 待执行任务 ({len(pending)}):")
        for t in pending:
            print(f"  [{t['task_id']}] {t['task_name']}")

        print(f"\n✅ 已完成任务 ({len(completed)}):")
        for t in completed:
            print(f"  [{t['task_id']}] {t['task_name']}")

    def print_execution_results(self):
        """输出执行结果"""
        print("\n" + "=" * 60)
        print("📊 执行结果汇总")
        print("=" * 60)

        completed = self.task_store.get_completed_tasks()
        for t in completed:
            print(f"\n[{t['task_id']}] {t['task_name']}")
            print(f"   结果: {t['result'][:200]}...")

    def run(self, max_iterations: int = 10):
        """运行BabyAGI主循环"""
        print("\n" + "=" * 60)
        print("🌸 BabyAGI 鲜花存储策略系统启动")
        print("=" * 60)
        print(f"🎯 目标: {self.objective}")

        iteration = 0
        while iteration < max_iterations:
            print(f"\n{'='*60}")
            print(f"📌 第 {iteration + 1} 轮执行")
            print("=" * 60)

            task = get_next_task(self.task_store)
            if not task:
                print("✅ 所有任务已完成！")
                break

            print(f"\n🔄 执行任务 [{task['task_id']}]: {task['task_name']}")

            result = execute_task(
                self.model, task, self.task_store, self.knowledge_vectorstore
            )
            print(f"✅ 结果: {result[:150]}...")
            self.execution_results.append({"task": task, "result": result})

            self.print_task_list()

            print("\n🔄 正在生成新任务...")
            try:
                p_keys = ["https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY", "all_proxy", "ALL_PROXY"]
                p_backup = {k: os.environ.pop(k, None) for k in p_keys}

                try:
                    new_tasks_text = self.task_creation_chain.invoke({
                        "objective": self.objective,
                        "last_task": task["task_name"],
                        "result": result
                    })

                    if new_tasks_text.strip():
                        new_tasks = [t.strip() for t in new_tasks_text.split("\n") if t.strip()]
                        print(f"📝 生成 {len(new_tasks)} 个新任务:")
                        for t in new_tasks:
                            task_id = self.task_store.add_task(t)
                            print(f"  + [{task_id}] {t}")
                    else:
                        print("🎯 目标已达成，停止生成新任务")
                        break
                finally:
                    for k, v in p_backup.items():
                        if v: os.environ[k] = v

            except Exception as e:
                print(f"⚠️ 生成新任务失败: {e}")

            iteration += 1

        print("\n" + "=" * 60)
        print("🎉 BabyAGI 执行完成")
        print("=" * 60)
        self.print_execution_results()

        if self.execution_results:
            print("\n" + "=" * 60)
            print("💡 最终策略建议:")
            print("=" * 60)
            print(self.execution_results[-1]["result"])


# ================= 主执行部分 =================

if __name__ == "__main__":
    OBJECTIVE = "分析北京市今天的气候情况，并提出鲜花储存策略"

    baby_agi = BabyAGI(objective=OBJECTIVE, data_dir="./data")

    baby_agi.add_initial_task(
        f"获取并分析当前北京市的气候信息（温度、湿度、天气状况）"
    )

    baby_agi.run(max_iterations=8)