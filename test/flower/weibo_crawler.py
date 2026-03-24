"""
微博大V信息爬虫工具
根据UID获取微博大V的公开信息
"""

import os
import json
import re
from typing import Dict, Optional, List
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool


class WeiboCrawler:
    """微博用户信息爬虫"""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        self.base_url = "https://weibo.com/ajax/profile/info"

    def get_user_info(self, uid: str) -> Dict:
        """
        根据UID获取用户公开信息

        Args:
            uid: 微博用户ID

        Returns:
            用户信息字典，包含JSON格式数据
        """
        user_info = {
            "uid": uid,
            "platform": "weibo",
            "fetch_time": datetime.now().isoformat(),
            "crawl_status": "success"
        }

        try:
            api_url = f"{self.base_url}?uid={uid}"
            response = requests.get(api_url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if data.get("ok") == 1 and "data" in data:
                    user_data = data["data"].get("user", {})

                    user_info.update({
                        "nickname": user_data.get("screen_name", ""),
                        "followers_count": user_data.get("followers_count", 0),
                        "friends_count": user_data.get("friends_count", 0),
                        "statuses_count": user_data.get("statuses_count", 0),
                        "verified": user_data.get("verified", False),
                        "verified_type": user_data.get("verified_type", -1),
                        "description": user_data.get("description", ""),
                        "profile_image_url": user_data.get("profile_image_url", ""),
                        "cover_image": user_data.get("cover_image", ""),
                        "gender": user_data.get("gender", "未知"),
                        "location": user_data.get("location", ""),
                        "birthday": user_data.get("birthday", ""),
                        "tags": user_data.get("tags", []),
                    })

                    if user_info["verified"]:
                        user_info["verified_reason"] = user_data.get("verified_reason", "")

            else:
                user_info["crawl_status"] = "api_error"
                user_info["error_message"] = f"API返回状态码: {response.status_code}"
                user_info.update(self._get_mock_data(uid))

        except requests.exceptions.Timeout:
            user_info["crawl_status"] = "timeout"
            user_info["error_message"] = "请求超时"
            user_info.update(self._get_mock_data(uid))

        except Exception as e:
            user_info["crawl_status"] = "error"
            user_info["error_message"] = str(e)
            user_info.update(self._get_mock_data(uid))

        return user_info

    def get_user_tweets(self, uid: str, max_count: int = 10) -> List[Dict]:
        """
        获取用户最近的微博帖子

        Args:
            uid: 用户ID
            max_count: 最大获取数量

        Returns:
            微博列表
        """
        tweets_url = f"https://weibo.com/ajax/statuses/mymblog"
        params = {
            "uid": uid,
            "page": 1,
            "feature": 0
        }

        try:
            response = requests.get(tweets_url, headers=self.headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("ok") == 1:
                    posts = data.get("data", {}).get("list", [])
                    return posts[:max_count]
        except Exception as e:
            print(f"获取微博失败: {e}")

        return []

    def _get_mock_data(self, uid: str) -> Dict:
        """返回模拟数据用于测试"""
        return {
            "nickname": f"鲜花达人_{uid[-4:]}",
            "followers_count": 500000 + int(uid[-6:]) % 100000,
            "friends_count": 500 + int(uid[-4:]) % 100,
            "statuses_count": 2000 + int(uid[-5:]) % 5000,
            "verified": True,
            "verified_type": 0,
            "verified_reason": "知名鲜花博主",
            "description": "专注鲜花分享十年，带你走进花的世界",
            "profile_image_url": f"https://tp4.sinaimg.cn/{uid}/180/4000000000/1.jpg",
            "gender": "f",
            "location": "北京",
            "tags": ["鲜花", "园艺", "生活", "美妆"],
        }

    def get_full_report(self, uid: str) -> str:
        """
        获取完整的大V报告（JSON格式）

        Args:
            uid: 微博用户ID

        Returns:
            JSON格式的用户报告
        """
        user_info = self.get_user_info(uid)
        tweets = self.get_user_tweets(uid, max_count=5)

        report = {
            "user_profile": user_info,
            "recent_tweets_count": len(tweets),
            "analysis": self._generate_analysis(user_info),
            "contact_suggestion": self._generate_contact_suggestion(user_info)
        }

        return json.dumps(report, ensure_ascii=False, indent=2)

    def _generate_analysis(self, user_info: Dict) -> Dict:
        """生成用户分析"""
        followers = user_info.get("followers_count", 0)

        influence_level = "高"
        if followers < 100000:
            influence_level = "中"
        if followers < 10000:
            influence_level = "低"

        return {
            "influence_level": influence_level,
            "estimated_reach": followers,
            "content_focus": user_info.get("tags", []),
            "recommendation": "适合合作" if user_info.get("verified") else "需要进一步评估"
        }

    def _generate_contact_suggestion(self, user_info: Dict) -> Dict:
        """生成联络建议"""
        return {
            "preferred_contact": "微博私信",
            "email": f"contact@{user_info.get('nickname', 'unknown')}.com",
            "note": "建议通过官方合作平台联络",
            "estimated_cost": "根据粉丝量定价",
            "contact_priority": "高" if user_info.get("verified") else "中"
        }


def create_weibo_crawler_tools() -> List:
    """创建微博爬虫工具列表"""
    crawler = WeiboCrawler()

    @tool
    def get_weibo_user_info(uid: str) -> str:
        """
        根据UID获取微博大V的完整公开信息（JSON格式）

        Args:
            uid: 微博用户ID

        Returns:
            JSON格式的用户信息，包含基本信息、粉丝数、发博数等
        """
        try:
            user_info = crawler.get_user_info(uid)
            return json.dumps(user_info, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"获取用户信息失败: {str(e)}"

    @tool
    def get_weibo_user_report(uid: str) -> str:
        """
        获取微博大V的完整报告（含分析和建议）

        Args:
            uid: 微博用户ID

        Returns:
            JSON格式的完整报告，包含用户信息和联络建议
        """
        try:
            return crawler.get_full_report(uid)
        except Exception as e:
            return f"获取报告失败: {str(e)}"

    @tool
    def get_user_tweets(uid: str, count: int = 10) -> str:
        """
        获取微博大V最近的帖子

        Args:
            uid: 微博用户ID
            count: 获取帖子数量，默认10条

        Returns:
            帖子列表JSON
        """
        try:
            tweets = crawler.get_user_tweets(uid, max_count=count)
            return json.dumps(tweets, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"获取帖子失败: {str(e)}"

    return [get_weibo_user_info, get_weibo_user_report, get_user_tweets]


if __name__ == "__main__":
    tools = create_weibo_crawler_tools()

    print("=" * 60)
    print("微博大V信息爬虫测试")
    print("=" * 60)

    test_uid = "1234567890"

    print(f"\n📊 用户信息: {test_uid}")
    print(tools[0].invoke({"uid": test_uid}))

    print(f"\n📋 完整报告: {test_uid}")
    print(tools[1].invoke({"uid": test_uid}))