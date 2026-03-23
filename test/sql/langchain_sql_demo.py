import os
from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from langchain_classic.chains import create_sql_query_chain
from langchain_community.chat_models import ChatTongyi

load_dotenv()

os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)

API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not API_KEY:
    raise EnvironmentError("请检查 .env 文件中的 API Key 配置")

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "flower_shop")

if not MYSQL_PASSWORD:
    raise EnvironmentError("请检查 .env 文件中的 MYSQL_PASSWORD 配置")

db_uri = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
db = SQLDatabase.from_uri(db_uri)

print("数据库表结构:", db.table_info)

llm = ChatTongyi(model="qwen-plus", api_key=API_KEY)

chain = create_sql_query_chain(llm, db)


# 运行与鲜花运营相关的问题
response = chain.invoke({"question": "有多少种不同的鲜花？"})
print(response)

response = chain.invoke({"question": "哪种鲜花的存货数量最少？"})
print(response)

response = chain.invoke({"question": "平均销售价格是多少？"})
print(response)

