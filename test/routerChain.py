import os
from dotenv import load_dotenv
from langchain_community.chat_models import ChatTongyi
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel, Field
from typing import Literal

load_dotenv()

# 1. 初始化模型
llm = ChatTongyi(
    model="qwen-turbo",
    dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
    temperature=0.7
)

# 2. 定义路由输出结构
class RouteQuery(BaseModel):
    destination: Literal["flower_care", "flower_decoration", "DEFAULT"] = Field(
        description="选择的目标链"
    )

# 3. 定义各场景模板
flower_care_template = """你是一个经验丰富的园丁，擅长解答关于养花育花的问题。
下面是需要你来回答的问题:
{input}"""

flower_deco_template = """你是一位网红插花大师，擅长解答关于鲜花装饰的问题。
下面是需要你来回答的问题:
{input}"""

# 4. 构建各场景链（LCEL风格）
flower_care_chain = PromptTemplate.from_template(flower_care_template) | llm
flower_deco_chain = PromptTemplate.from_template(flower_deco_template) | llm
default_chain = PromptTemplate.from_template("{input}") | llm  # 简单默认链

# 5. 构建路由提示
router_prompt = PromptTemplate.from_template(
    "根据用户问题，选择最适合回答的专家类型。\n"
    "选项：\n"
    "- flower_care: 适合回答关于鲜花护理的问题\n"
    "- flower_decoration: 适合回答关于鲜花装饰的问题\n"
    "如果都不适合，选择默认。\n"
    "用户问题：{input}"
)

# 6. 路由链（输出结构化结果）
router_chain = router_prompt | llm.with_structured_output(RouteQuery)

# 7. 路由与执行函数
def route_and_execute(inputs: dict) -> str:
    # 先路由
    route_result = router_chain.invoke({"input": inputs["input"]})
    # 根据目的地选择对应链并执行
    if route_result.destination == "flower_care":
        return flower_care_chain.invoke({"input": inputs["input"]})
    elif route_result.destination == "flower_decoration":
        return flower_deco_chain.invoke({"input": inputs["input"]})
    else:
        return default_chain.invoke({"input": inputs["input"]})

# 8. 构建最终链
chain = RunnableLambda(route_and_execute)

# 9. 调用
result = chain.invoke({"input": "如何为婚礼场地装饰花朵？"})
print(result)