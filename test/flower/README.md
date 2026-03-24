# 微博鲜花推广大V搜寻系统

## 项目目标

帮助市场营销部门的员工找到微博上适合做鲜花推广的大V，并给出具体的联络方案。

## 技术方案

### 第一步：微博UID搜索

使用 LangChain 的搜索工具，通过 SerpAPI 的 `getUID` 工具，以模糊搜索方式找到对鲜花推广感兴趣的大V。

**工具函数：**
- `search_weibo_influencers()` - 搜索相关领域的微博博主
- `get_uid_by_username()` - 根据用户名获取UID

### 第二步：大V信息爬取

根据微博 UID，通过爬虫工具获取大V的微博公开信息，返回 JSON 格式数据。

**工具函数：**
- `get_weibo_user_info()` - 获取用户基本信息
- `get_weibo_user_report()` - 获取完整报告（含分析和建议）
- `get_user_tweets()` - 获取最近帖子

## 文件结构

```
flower/
├── weibo_search.py      # SerpAPI搜索工具
├── weibo_crawler.py     # 微博爬虫工具
├── weibo_agent.py       # 主Agent程序
├── config.json          # 配置文件
└── requirements.txt     # 依赖
```

## 环境配置

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export DASHSCOPE_API_KEY="your_key"
export SERPAPI_API_KEY="your_key"
```

## 运行方式

```bash
cd test/flower

# 交互模式
python weibo_agent.py

# 命令行模式
python weibo_agent.py 玫瑰花 鲜花
```

## Agent 工作流程

1. **搜索阶段**：使用关键词模糊搜索微博博主
2. **获取UID**：提取匹配大V的用户ID
3. **信息爬取**：根据UID获取详细用户信息
4. **分析建议**：生成联络方案和合作建议