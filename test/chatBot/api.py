"""
聊天机器人 API
基于 FastAPI
"""

import os
import sys
import time
import threading
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv

load_dotenv()

for var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
    os.environ.pop(var, None)
os.environ['NO_PROXY'] = '*'

from pydantic import BaseModel
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from chatBot.chatbot import ChatBot
from chatBot.tools.order_tool import get_order_tool, RedisHashCache, get_order_cache

app = FastAPI(
    title="内部员工聊天机器人",
    description="支持 RAG + 订单查询 + 记忆功能",
    version="1.0.0",
    docs_url=None,
    redoc_url="/docs"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>内部员工聊天机器人</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdn.jsdelivr.net/npm/font-awesome@6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .chat-container { height: calc(100vh - 200px); }
        .message-user { background: #3b82f6; color: white; }
        .message-bot { background: #f3f4f6; color: #1f2937; }
        .typing { display: inline-block; }
        .typing::after { content: '...'; animation: typing 1.5s infinite; }
        @keyframes typing { 0%, 100% { opacity: 0.3; } 50% { opacity: 1; } }
    </style>
</head>
<body class="p-4">
    <div class="max-w-4xl mx-auto bg-white rounded-2xl shadow-2xl overflow-hidden">
        <div class="bg-gradient-to-r from-indigo-600 to-purple-600 p-4">
            <h1 class="text-white text-xl font-bold"><i class="fas fa-robot mr-2"></i>内部员工聊天机器人</h1>
            <p class="text-indigo-100 text-sm">RAG知识库 | 订单查询 | 智能记忆</p>
        </div>
        
        <div class="p-4 bg-gray-50 border-b">
            <div class="flex gap-2">
                <button onclick="initChat()" class="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition">
                    <i class="fas fa-play mr-1"></i>初始化
                </button>
                <button onclick="clearHistory()" class="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition">
                    <i class="fas fa-trash mr-1"></i>清除历史
                </button>
                <button onclick="clearCache()" class="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition">
                    <i class="fas fa-broom mr-1"></i>清除缓存
                </button>
                <button onclick="showCacheStatus()" class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition">
                    <i class="fas fa-database mr-1"></i>缓存状态
                </button>
            </div>
            <div id="status" class="mt-2 text-sm text-gray-600"></div>
        </div>
        
        <div class="chat-container p-4 overflow-y-auto" id="chatBox"></div>
        
        <div class="p-4 border-t">
            <div class="flex gap-2">
                <input type="text" id="messageInput" placeholder="输入消息... (支持订单查询如: ORD20260324001)"
                    class="flex-1 px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    onkeypress="if(event.key==='Enter')sendMessage()">
                <button onclick="sendMessage()" class="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition">
                    <i class="fas fa-paper-plane"></i>
                </button>
            </div>
        </div>
    </div>
    
    <script>
        let sessionId = 'session_' + Date.now();
        
        function log(msg) {
            document.getElementById('status').innerHTML = '<i class="fas fa-info-circle mr-1"></i>' + msg;
        }
        
        async function initChat() {
            log('初始化中...');
            try {
                const res = await fetch('/init', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        knowledge_dir: '/Users/cc/Code/langchain/test/OneFlower'
                    })
                });
                const data = await res.json();
                if (data.code === 200) {
                    log('<span class="text-green-600">初始化成功!</span>');
                } else {
                    log('<span class="text-red-600">初始化失败: ' + data.message + '</span>');
                }
            } catch(e) { log('初始化失败: ' + e); }
        }
        
        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            if (!message) return;
            
            addMessage('user', message);
            input.value = '';
            
            const botMsg = addMessage('bot', '<span class="typing">思考中</span>');
            
            try {
                const res = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message, session_id: sessionId})
                });
                const data = await res.json();
                if (data.code === 200) {
                    botMsg.innerHTML = data.data.response.replace(/\\n/g, '<br>');
                } else {
                    botMsg.innerHTML = '<span class="text-red-500">' + data.message + '</span>';
                }
            } catch(e) {
                botMsg.innerHTML = '<span class="text-red-500">请求失败: ' + e + '</span>';
            }
        }
        
        function addMessage(type, content) {
            const chatBox = document.getElementById('chatBox');
            const div = document.createElement('div');
            div.className = 'mb-3 ' + (type === 'user' ? 'text-right' : 'text-left');
            div.innerHTML = '<div class="inline-block max-w-[80%] p-3 rounded-lg message-' + type + '">' + content + '</div>';
            chatBox.appendChild(div);
            chatBox.scrollTop = chatBox.scrollHeight;
            return div;
        }
        
        async function clearHistory() {
            try {
                const res = await fetch('/history/' + sessionId, {method: 'DELETE'});
                const data = await res.json();
                log(data.code === 200 ? '<span class="text-green-600">历史已清除</span>' : data.message);
                document.getElementById('chatBox').innerHTML = '';
            } catch(e) { log('清除失败: ' + e); }
        }
        
        async function clearCache() {
            try {
                const res = await fetch('/cache/clear', {method: 'POST'});
                const data = await res.json();
                log(data.code === 200 ? '<span class="text-green-600">缓存已清除 (' + data.data.cleared_count + '条)</span>' : data.message);
            } catch(e) { log('清除失败: ' + e); }
        }
        
        async function showCacheStatus() {
            try {
                const res = await fetch('/cache/status');
                const data = await res.json();
                if (data.data && data.data.connected) {
                    log('缓存状态: ' + data.data.cached_orders + '个订单, 内存: ' + data.data.used_memory);
                } else {
                    log('Redis未连接');
                }
            } catch(e) { log('查询失败: ' + e); }
        }
        
        window.onload = function() {
            document.getElementById('messageInput').focus();
        };
    </script>
</body>
</html>
"""


class InitRequest(BaseModel):
    knowledge_dir: str = ""
    persist_directory: str = "./chroma_db"
    embedding_model: str = "text-embedding-v2"
    llm_model: str = "qwen-turbo"
    chunk_size: int = 500
    chunk_overlap: int = 50
    temperature: float = 0.7
    top_k: int = 3
    rebuild: bool = False


class ChatRequest(BaseModel):
    message: str = ""
    session_id: str = "default"


class CacheConfig(BaseModel):
    clear_interval: int = 3600
    enabled: bool = True


chatbot_instance = {"bot": None}
cache_timer = {"thread": None, "enabled": False}


def clear_order_cache_task(interval: int = 3600):
    while cache_timer.get("enabled", False):
        time.sleep(interval)
        if cache_timer.get("enabled", False):
            try:
                tool = get_order_tool()
                count = tool.clear_order_cache()
                print(f"🧹 定时任务: 已清除 {count} 条订单缓存")
            except Exception as e:
                print(f"🧹 定时任务执行失败: {e}")


def start_cache_timer(interval: int = 3600):
    if cache_timer.get("enabled", False):
        return
    cache_timer["enabled"] = True
    cache_timer["thread"] = threading.Thread(target=clear_order_cache_task, args=(interval,), daemon=True)
    cache_timer["thread"].start()
    print(f"✅ 定时清除缓存任务已启动，间隔: {interval}秒")


def stop_cache_timer():
    cache_timer["enabled"] = False
    cache_timer["thread"] = None
    print("🛑 定时清除缓存任务已停止")


@app.get("/", response_class=HTMLResponse)
async def index():
    """可视化界面"""
    return HTML_TEMPLATE


@app.get("/api", tags=["API"])
async def api_docs():
    """API 文档跳转"""
    return {"message": "API文档", "docs": "/docs", "redoc": "/redoc"}


@app.post("/init", tags=["初始化"])
async def init_chatbot(req: InitRequest = None):
    if req is None or not req.knowledge_dir:
        return {"code": 400, "message": "请提供 knowledge_dir 参数", "data": None}
    
    knowledge_dir = req.knowledge_dir if os.path.isabs(req.knowledge_dir) else str(BASE_DIR / req.knowledge_dir)
    persist_directory = req.persist_directory if os.path.isabs(req.persist_directory) else str(BASE_DIR / req.persist_directory)
    
    try:
        bot = ChatBot(
            knowledge_dir=knowledge_dir,
            persist_directory=persist_directory,
            embedding_model=req.embedding_model,
            llm_model=req.llm_model,
            chunk_size=req.chunk_size,
            chunk_overlap=req.chunk_overlap,
            temperature=req.temperature,
            top_k=req.top_k,
            rebuild=req.rebuild
        )
        chatbot_instance["bot"] = bot
        return {"code": 200, "message": "初始化成功", "data": {"status": "ok"}}
    except Exception as e:
        return {"code": 500, "message": f"初始化失败: {str(e)}", "data": None}


@app.post("/chat", tags=["对话"])
async def chat(req: ChatRequest = None):
    if req is None or not req.message:
        return {"code": 400, "message": "请提供 message 参数", "data": None}
    
    if chatbot_instance.get("bot") is None:
        return {"code": 400, "message": "请先调用 /init 接口初始化", "data": None}
    
    try:
        response = chatbot_instance["bot"].chat(req.message, req.session_id)
        return {"code": 200, "message": "success", "data": {"response": response, "session_id": req.session_id}}
    except Exception as e:
        return {"code": 500, "message": f"请求失败: {str(e)}", "data": None}


@app.get("/history/{session_id}", tags=["历史"])
async def get_history(session_id: str):
    if chatbot_instance.get("bot") is None:
        return {"code": 400, "message": "请先初始化", "data": None}
    
    history = chatbot_instance["bot"].get_history(session_id)
    messages = [{"type": msg.type, "content": msg.content} for msg in history]
    return {"code": 200, "message": "success", "data": messages}


@app.delete("/history/{session_id}", tags=["历史"])
async def clear_history(session_id: str):
    if chatbot_instance.get("bot") is None:
        return {"code": 400, "message": "请先初始化", "data": None}
    
    chatbot_instance["bot"].clear_history(session_id)
    chatbot_instance["bot"].clear_order_history(session_id)
    return {"code": 200, "message": "success", "data": None}


@app.post("/cache/clear", tags=["缓存管理"])
async def clear_cache():
    try:
        tool = get_order_tool()
        count = tool.clear_order_cache()
        return {"code": 200, "message": "success", "data": {"cleared_count": count}}
    except Exception as e:
        return {"code": 500, "message": f"清除缓存失败: {str(e)}", "data": None}


@app.post("/cache/timer", tags=["缓存管理"])
async def config_cache_timer(config: CacheConfig = None):
    if config is None:
        config = CacheConfig()
    
    if config.enabled:
        start_cache_timer(config.clear_interval)
        return {"code": 200, "message": "定时任务已启动", "data": {"interval": config.clear_interval}}
    else:
        stop_cache_timer()
        return {"code": 200, "message": "定时任务已停止", "data": None}


@app.get("/cache/status", tags=["缓存管理"])
async def cache_status():
    try:
        tool = get_order_tool()
        if tool.cache:
            client = tool.cache._get_client()
            if client:
                info = client.info("memory")
                keys = tool.cache.get_keys()
                return {
                    "code": 200,
                    "message": "success",
                    "data": {
                        "connected": True,
                        "used_memory": info.get("used_memory_human", "N/A"),
                        "ttl": tool.cache.ttl,
                        "cached_orders": len(keys),
                        "order_ids": keys[:10]
                    }
                }
        return {"code": 200, "message": "success", "data": {"connected": False}}
    except Exception as e:
        return {"code": 500, "message": str(e), "data": None}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
