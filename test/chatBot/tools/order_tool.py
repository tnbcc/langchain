"""
订单查询工具 - 支持 Redis Hash 缓存
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dotenv import load_dotenv

load_dotenv()

for var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
    os.environ.pop(var, None)
os.environ['NO_PROXY'] = '*'

# MySQL 配置
DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", 3306)),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "flower_shop"),
    "charset": "utf8mb4"
}

# Redis 配置
REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST", "localhost"),
    "port": int(os.getenv("REDIS_PORT", 6379)),
    "password": os.getenv("REDIS_PASSWORD", None) or None,
    "db": int(os.getenv("REDIS_DB", 0)),
    "decode_responses": True
}

REDIS_TTL = int(os.getenv("REDIS_TTL", 86400))  # 默认1天


class RedisHashCache:
    """Redis Hash 缓存管理器"""
    
    def __init__(self, key_prefix: str = "order", ttl: int = REDIS_TTL):
        self.key_prefix = key_prefix
        self.ttl = ttl
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            import redis
            try:
                self._client = redis.Redis(**REDIS_CONFIG)
                self._client.ping()
            except Exception as e:
                print(f"Redis 连接失败: {e}")
                return None
        return self._client
    
    def _make_key(self, order_id: str) -> str:
        """生成 Redis key"""
        return f"{self.key_prefix}:{order_id}"
    
    def hset(self, order_id: str, data: Dict, ttl: Optional[int] = None) -> bool:
        """设置 Hash 缓存"""
        client = self._get_client()
        if not client:
            return False
        
        try:
            key = self._make_key(order_id)
            client.hset(key, mapping=data)
            client.expire(key, ttl or self.ttl)
            return True
        except Exception as e:
            print(f"Redis hset 失败: {e}")
            return False
    
    def hget(self, order_id: str) -> Optional[Dict]:
        """获取 Hash 缓存"""
        client = self._get_client()
        if not client:
            return None
        
        try:
            key = self._make_key(order_id)
            data = client.hgetall(key)
            if data:
                return data
        except Exception as e:
            print(f"Redis hget 失败: {e}")
        return None
    
    def hgetall_pattern(self, pattern: str = "*") -> Dict[str, Dict]:
        """根据模式获取所有匹配的 Hash"""
        client = self._get_client()
        if not client:
            return {}
        
        try:
            keys = client.keys(f"{self.key_prefix}:{pattern}")
            result = {}
            for key in keys:
                order_id = key.replace(f"{self.key_prefix}:", "")
                data = client.hgetall(key)
                if data:
                    result[order_id] = data
            return result
        except Exception as e:
            print(f"Redis hgetall_pattern 失败: {e}")
            return {}
    
    def delete(self, order_id: str) -> bool:
        """删除 Hash 缓存"""
        client = self._get_client()
        if not client:
            return False
        
        try:
            client.delete(self._make_key(order_id))
            return True
        except Exception as e:
            print(f"Redis delete 失败: {e}")
            return False
    
    def delete_pattern(self, pattern: str = "*") -> int:
        """根据模式删除缓存"""
        client = self._get_client()
        if not client:
            return 0
        
        try:
            keys = client.keys(f"{self.key_prefix}:{pattern}")
            if keys:
                return client.delete(*keys)
        except Exception as e:
            print(f"Redis delete_pattern 失败: {e}")
        return 0
    
    def clear_all(self) -> bool:
        """清空所有缓存"""
        return self.delete_pattern("*") > 0
    
    def get_keys(self) -> List[str]:
        """获取所有缓存的 key"""
        client = self._get_client()
        if not client:
            return []
        
        try:
            keys = client.keys(f"{self.key_prefix}:*")
            return [k.replace(f"{self.key_prefix}:", "") for k in keys]
        except Exception as e:
            print(f"Redis get_keys 失败: {e}")
            return []


# 全局缓存实例
_order_cache = None


def get_order_cache() -> RedisHashCache:
    """获取订单缓存实例"""
    global _order_cache
    if _order_cache is None:
        _order_cache = RedisHashCache()
    return _order_cache


class OrderQueryTool:
    """订单查询工具 - 支持 Redis Hash 缓存"""
    
    def __init__(self, db_config: Optional[Dict] = None, use_cache: bool = True):
        self.db_config = db_config or DB_CONFIG
        self.use_cache = use_cache
        self.cache = get_order_cache() if use_cache else None
    
    def _get_connection(self):
        import pymysql
        return pymysql.connect(**self.db_config)
    
    def _get_order_from_db(self, order_id: str) -> Optional[Dict]:
        """从数据库查询订单"""
        conn = self._get_connection()
        
        try:
            with conn.cursor() as cursor:
                sql = """
                    SELECT 
                        o.order_id, f.flower_name, f.flower_type,
                        o.quantity, o.unit_price, o.total_price,
                        o.phone, o.shipping_status, o.shipping_time,
                        o.return_status, o.created_at, o.return_time
                    FROM orders o
                    JOIN flowers f ON o.flower_id = f.id
                    WHERE o.order_id = %s
                """
                cursor.execute(sql, (order_id,))
                result = cursor.fetchone()
                
                if not result:
                    return None
                
                return {
                    "order_id": str(result[0]),
                    "flower_name": str(result[1]),
                    "flower_type": str(result[2]),
                    "quantity": int(result[3]),
                    "unit_price": str(result[4]),
                    "total_price": str(result[5]),
                    "phone": str(result[6]) if result[6] else "",
                    "shipping_status": str(result[7]) if result[7] else "",
                    "shipping_time": str(result[8]) if result[8] else "",
                    "return_status": str(result[9]) if result[9] else "",
                    "created_at": str(result[10]) if result[10] else "",
                    "return_time": str(result[11]) if result[11] else ""
                }
        except Exception as e:
            print(f"数据库查询失败: {e}")
            return None
        finally:
            conn.close()
    
    def _format_order_response(self, order_data: Dict) -> str:
        """格式化订单响应"""
        status_map = {"pending": "待发货", "shipped": "已发货", "delivered": "已送达"}
        return_map = {"none": "无退货", "applied": "申请退货中", "approved": "已批准退货", "rejected": "已拒绝退货", "completed": "已完成退货"}
        
        shipping_time = order_data.get("shipping_time", "")
        return_time = order_data.get("return_time", "")
        
        shipping_time_str = f"\n发货时间: {shipping_time}" if shipping_time else ""
        return_time_str = f"\n退货时间: {return_time}" if return_time else ""
        
        return f"""📦 订单信息
订单号: {order_data.get('order_id', '')}
商品名称: {order_data.get('flower_name', '')}
商品类型: {order_data.get('flower_type', '')}
购买数量: {order_data.get('quantity', '')}
单价: ¥{order_data.get('unit_price', '')}
总价: ¥{order_data.get('total_price', '')}
联系电话: {order_data.get('phone', '')}
发货状态: {status_map.get(order_data.get('shipping_status', ''), order_data.get('shipping_status', ''))}{shipping_time_str}
退货状态: {return_map.get(order_data.get('return_status', ''), order_data.get('return_status', ''))}{return_time_str}
下单时间: {order_data.get('created_at', '')}"""
    
    def query_order(self, order_id: str, use_cache: bool = None) -> str:
        """查询订单 - 支持 Hash 缓存"""
        use_cache_flag = use_cache if use_cache is not None else self.use_cache
        
        # 先从缓存获取
        if use_cache_flag and self.cache:
            cached_data = self.cache.hget(order_id)
            if cached_data:
                return self._format_order_response(cached_data)
        
        # 从数据库获取
        order_data = self._get_order_from_db(order_id)
        
        if not order_data:
            return f"未找到订单号 {order_id} 的订单信息"
        
        # 缓存结果 (Hash 结构)
        if use_cache_flag and self.cache:
            self.cache.hset(order_id, order_data)
        
        return self._format_order_response(order_data)
    
    def query_order_by_phone(self, phone: str) -> str:
        """根据手机号查询订单列表"""
        conn = self._get_connection()
        
        try:
            with conn.cursor() as cursor:
                sql = """
                    SELECT 
                        o.order_id, f.flower_name, o.quantity, 
                        o.total_price, o.shipping_status, o.shipping_time, o.created_at
                    FROM orders o
                    JOIN flowers f ON o.flower_id = f.id
                    WHERE o.phone = %s
                    ORDER BY o.created_at DESC
                    LIMIT 10
                """
                cursor.execute(sql, (phone,))
                results = cursor.fetchall()
                
                if not results:
                    return f"未找到手机号 {phone} 的订单信息"
                
                status_map = {"pending": "待发货", "shipped": "已发货", "delivered": "已送达"}
                
                msg = f"📋 手机号 {phone} 的订单列表：\n"
                for r in results:
                    shipping_time = f" 发货:{r[5]}" if r[5] else ""
                    msg += f"订单号: {r[0]} 商品: {r[1]}x{r[2]} 金额: ¥{r[3]} 状态:{status_map.get(r[4], r[4])}{shipping_time}\n"
                
                return msg
        except Exception as e:
            return f"查询失败: {str(e)}"
        finally:
            conn.close()
    
    def clear_order_cache(self, order_id: str = None) -> int:
        """清除订单缓存"""
        if not self.cache:
            return 0
        
        if order_id:
            return 1 if self.cache.delete(order_id) else 0
        else:
            return self.cache.delete_pattern("*")
    
    def clear_all_cache(self) -> bool:
        """清空所有缓存"""
        if not self.cache:
            return False
        return self.cache.clear_all()
    
    def get_cache_keys(self) -> List[str]:
        """获取所有缓存的订单ID"""
        if not self.cache:
            return []
        return self.cache.get_keys()


from langchain_core.tools import tool

_order_tool_instance = None


def get_order_tool() -> OrderQueryTool:
    global _order_tool_instance
    if _order_tool_instance is None:
        _order_tool_instance = OrderQueryTool()
    return _order_tool_instance


@tool
def query_order(order_id: str) -> str:
    """查询订单信息，输入订单号，返回订单详情"""
    return get_order_tool().query_order(order_id)


@tool
def query_order_by_phone(phone: str) -> str:
    """根据手机号查询订单列表"""
    return get_order_tool().query_order_by_phone(phone)
