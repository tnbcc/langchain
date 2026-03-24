"""
微博UID搜索工具 - 使用SerpAPI
通过模糊搜索找到可能对鲜花推广感兴趣的大V
"""

import os
import json
from typing import List, Optional, Dict
from langchain_core.tools import tool

try:
    from langchain_community.utilities.serpapi import SerpAPIWrapper
    SERPAPI_AVAILABLE = True
except ImportError:
    SERPAPI_AVAILABLE = False


class WeiboSearchTool:
    """微博搜索工具 - 基于SerpAPI"""

    def __init__(self):
        self.api_key = os.getenv("SERPAPI_API_KEY")
        self.serpapi = None

        if self.api_key and SERPAPI_AVAILABLE:
            try:
                self.serpapi = SerpAPIWrapper(params={"engine": "baidu"})
                print("✅ SerpAPI已配置")
            except Exception as e:
                print(f"⚠️ SerpAPI初始化失败: {e}")
                self.serpapi = None
        else:
            print("⚠️ 未设置SERPAPI_API_KEY或模块不可用，将使用模拟数据")

    def search_weibo_users(self, keywords: str, num_results: int = 10) -> List[Dict]:
        """
        搜索微博用户
        
        Args:
            keywords: 搜索关键词，如"玫瑰花 博主"
            num_results: 返回结果数量
        
        Returns:
            用户列表，包含UID和基本信息
        """
        if not self.api_key:
            return self._mock_search_results(keywords)

        try:
            search_query = f"site:weibo.com {keywords}"
            results = self.serpapi.run(search_query)

            return self._parse_search_results(results, keywords)
        except Exception as e:
            print(f"搜索失败: {e}")
            return self._mock_search_results(keywords)

    def _parse_search_results(self, raw_results: str, keywords: str) -> List[Dict]:
        """解析搜索结果，提取微博用户信息"""
        users = []

        if "weibo.com/u/" in raw_results:
            import re
            uid_pattern = r'weibo\.com/u/(\d+)'
            uids = re.findall(uid_pattern, raw_results)

            for uid in set(uids):
                users.append({
                    "uid": uid,
                    "platform": "weibo",
                    "match_keywords": keywords,
                    "profile_url": f"https://weibo.com/u/{uid}"
                })

        return users

    def _mock_search_results(self, keywords: str) -> List[Dict]:
        """模拟搜索结果（用于测试）"""
        mock_uids = [
            {"uid": "1234567890", "nickname": "玫瑰花语", "platform": "weibo", "match_keywords": keywords},
            {"uid": "9876543210", "nickname": "鲜花控", "platform": "weibo", "match_keywords": keywords},
            {"uid": "5678901234", "nickname": "园艺生活家", "platform": "weibo", "match_keywords": keywords},
        ]
        return mock_uids

    def get_user_uid_by_name(self, username: str) -> Optional[str]:
        """
        根据用户名获取UID
        
        Args:
            username: 微博用户名
        
        Returns:
            UID字符串，未找到返回None
        """
        if not self.api_key:
            return f"MOCK_UID_{hash(username) % 100000}"

        try:
            search_query = f"site:weibo.com {username} 微博"
            results = self.serpapi.run(search_query)

            import re
            uid_pattern = r'weibo\.com/u/(\d+)'
            match = re.search(uid_pattern, results)

            if match:
                return match.group(1)
        except Exception as e:
            print(f"获取UID失败: {e}")

        return None


def create_weibo_search_tools() -> List[tool]:
    """创建微博搜索工具列表"""
    weibo_tool = WeiboSearchTool()

    @tool
    def search_weibo_influencers(keywords: str) -> str:
        """
        搜索微博上有影响力的鲜花相关博主。

        Args:
            keywords: 搜索关键词，例如"玫瑰花"、"鲜花"、"园艺"等

        Returns:
            匹配的微博大V列表，包含UID和个人主页链接
        """
        results = weibo_tool.search_weibo_users(keywords, num_results=10)

        if not results:
            return "未找到匹配的微博博主"

        output = "找到以下微博大V：\n\n"
        for i, user in enumerate(results, 1):
            output += f"{i}. UID: {user['uid']}\n"
            output += f"   主页: {user.get('profile_url', 'N/A')}\n"
            output += f"   匹配关键词: {user.get('match_keywords', keywords)}\n\n"

        return output

    @tool
    def get_uid_by_username(username: str) -> str:
        """
        根据微博用户名获取UID（getUID工具）

        Args:
            username: 微博用户名

        Returns:
            用户UID
        """
        uid = weibo_tool.get_user_uid_by_name(username)

        if uid:
            return f"用户名 {username} 的UID是: {uid}"
        else:
            return f"未找到用户 {username} 的UID"

    return [search_weibo_influencers, get_uid_by_username]


if __name__ == "__main__":
    tools = create_weibo_search_tools()

    print("=" * 60)
    print("微博UID搜索工具测试")
    print("=" * 60)

    result = tools[0].invoke({"keywords": "玫瑰花 博主 花卉"})
    print(result)

    result2 = tools[1].invoke({"username": "玫瑰花语"})
    print(result2)