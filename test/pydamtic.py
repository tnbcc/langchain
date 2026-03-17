import os
from dotenv import load_dotenv
from langchain_community.llms import Tongyi
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field 
import pandas as pd

load_dotenv()

# 1. 定义输出模型
class FlowerDescription(BaseModel):
    flower_type: str = Field(description="鲜花的种类")
    price: int = Field(description="鲜花的价格")
    description: str = Field(description="鲜花的描述文案")
    reason: str = Field(description="为什么要这样写这个文案")

# 2. 创建解析器并获取格式指令
parser = PydanticOutputParser(pydantic_object=FlowerDescription)
format_instructions = parser.get_format_instructions()

# 3. 初始化模型
llm = Tongyi(
    model="qwen-turbo",
    dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
    temperature=0.7
)

# 4. 创建提示模板（已注入格式指令）
prompt = PromptTemplate.from_template(
    "您是一位专业的鲜花店文案撰写员。\n"
    "对于售价为 {price} 元的 {flower} ，您能提供一个吸引人的简短中文描述吗？\n"
    "{format_instructions}",
    partial_variables={"format_instructions": format_instructions}
)

# 5. 构建 LCEL 链
chain = prompt | llm | parser

# 6. 准备输入数据
flowers = ["玫瑰", "百合", "康乃馨"]
prices = ["50", "30", "20"]
inputs = [{"flower": f, "price": p} for f, p in zip(flowers, prices)]

# 7. 批量执行链（返回已解析的 Pydantic 对象列表）
results = chain.batch(inputs)

# 8. 转换为 DataFrame（关键修改：使用 model_dump() 而不是 dict()）
df = pd.DataFrame([r.model_dump() for r in results])

print("输出的数据：", df.to_dict(orient='records'))