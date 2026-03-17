import logging
import os
from dotenv import load_dotenv
from flask import Flask, request, render_template

from langchain_community.llms import Tongyi
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import TextLoader, PyPDFLoader, Docx2txtLoader

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.retrievers.contextual_compression import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor
from langchain.chains import RetrievalQA


# 加载环境变量
load_dotenv()

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

if not DASHSCOPE_API_KEY:
    raise ValueError("请设置环境变量 DASHSCOPE_API_KEY")

logging.basicConfig(level=logging.INFO)


# 初始化 LLM
llm = Tongyi(
    model_name="qwen-turbo",
    dashscope_api_key=DASHSCOPE_API_KEY
)


# 文档加载函数
def load_documents(base_dir):
    documents = []

    for file in os.listdir(base_dir):
        file_path = os.path.join(base_dir, file)

        if file.endswith(".pdf"):
            loader = PyPDFLoader(file_path)
            documents.extend(loader.load())

        elif file.endswith(".docx"):
            loader = Docx2txtLoader(file_path)
            documents.extend(loader.load())

        elif file.endswith(".txt"):
            loader = TextLoader(file_path, encoding="utf-8")
            documents.extend(loader.load())

    return documents


# 构建向量数据库
def build_vectorstore():

    persist_dir = "vectorstore"

    embeddings = DashScopeEmbeddings(
        model="text-embedding-v1",
        dashscope_api_key=DASHSCOPE_API_KEY
    )

    if os.path.exists(persist_dir):
        logging.info("加载已有向量数据库...")
        vectordb = Chroma(
            persist_directory=persist_dir,
            embedding_function=embeddings
        )
    else:
        logging.info("创建新的向量数据库...")

        base_dir = "./OneFlower"

        docs = load_documents(base_dir)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100
        )

        texts = splitter.split_documents(docs)

        vectordb = Chroma.from_documents(
            texts,
            embeddings,
            persist_directory=persist_dir
        )

        vectordb.persist()

    return vectordb


# 初始化向量库
vectorstore = build_vectorstore()

retriever = vectorstore.as_retriever(search_kwargs={"k": 5})


# 创建压缩器
compressor = LLMChainExtractor.from_llm(llm)


# Contextual Compression Retriever
compression_retriever = ContextualCompressionRetriever(
    base_retriever=retriever,
    base_compressor=compressor
)


# RAG QA Chain
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=compression_retriever,
    return_source_documents=False
)


# Flask Web
app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def home():

    if request.method == "POST":

        question = request.form.get("question")

        if not question:
            return render_template("index.html", error="请输入问题")

        try:
            result = qa_chain.invoke({"query": question})
            answer = result["result"]

        except Exception as e:
            logging.error(e)
            answer = "系统出现错误"

        return render_template("index.html", result=answer)

    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)