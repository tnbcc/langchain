import os
from dotenv import load_dotenv
from langchain_community.llms import Tongyi
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

load_dotenv()

# 1. 初始化大模型
llm = Tongyi(
    model="qwen-turbo",
    dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
    temperature=0.7
)

# 2. 定义三个提示模板（与之前相同）
prompt1 = PromptTemplate.from_template(
    """你是一个植物学家。给定花的名称和类型，你需要为这种花写一个200字左右的介绍。

花名: {name}
颜色: {color}
植物学家: 这是关于上述花的介绍:"""
)

prompt2 = PromptTemplate.from_template(
    """你是一位鲜花评论家。给定一种花的介绍，你需要为这种花写一篇200字左右的评论。

鲜花介绍:
{introduction}
花评人对上述花的评论:"""
)

prompt3 = PromptTemplate.from_template(
    """你是一家花店的社交媒体经理。给定一种花的介绍和评论，你需要为这种花写一篇社交媒体的帖子，300字左右。

鲜花介绍:
{introduction}
花评人对上述花的评论:
{review}

社交媒体帖子:"""
)

# 3. 构建三个子链，每个都是可运行的组件（Runnable）
introduction_chain = prompt1 | llm | StrOutputParser()          # 输出：字符串（介绍）

review_chain = (
    RunnableLambda(lambda x: {"introduction": x["introduction"]})   # 从字典中提取 introduction 键
    | prompt2
    | llm
    | StrOutputParser()                                            # 输出：字符串（评论）
)

post_chain = (
    RunnableLambda(lambda x: {"introduction": x["introduction"], "review": x["review"]})
    | prompt3
    | llm
    | StrOutputParser()                                            # 输出：字符串（帖子）
)

# 4. 组合成完整的顺序链（LCEL 风格）
overall_chain = (
    RunnablePassthrough.assign(introduction=introduction_chain)   # 先计算 introduction
    .assign(review=review_chain)                                  # 然后计算 review（依赖 introduction）
    .assign(social_post_text=post_chain)                          # 最后计算 social_post_text（依赖 introduction 和 review）
)

# 5. 运行链并输出结果
result = overall_chain.invoke({"name": "玫瑰", "color": "黑色"})
print("生成的介绍：", result["introduction"])
print("生成的评论：", result["review"])
print("生成的社交媒体帖子：", result["social_post_text"])