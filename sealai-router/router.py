import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union, AsyncGenerator
import httpx
import yaml
import json
import logging
import asyncio
from datetime import datetime
import pytz
import tiktoken
import os
import time
import re
from contextlib import asynccontextmanager
import aiosqlite

# =====================================================================
# SYSTEM CONFIGURATION & AUTO-GENERATION
# =====================================================================
CONFIG_FILE = "config.yaml"
SQLITE_DB = "analytics.db"

DEFAULT_CONFIG = {
    "server": {"api_key": "sealai-admin", "port": 6767},
    "router_node": {
        "endpoint": "http://127.0.0.1:11434/v1",
        "model": "gemma-3-12b"
    },
    "providers": {
        "google": {"api_key": "YOUR_GOOGLE_KEY", "model": "gemini-2.5-flash"},
        "openai": {"api_key": "YOUR_OPENAI_KEY", "model": "gpt-5.2"},
        "local_worker": {"endpoint": "http://127.0.0.1:11435/v1", "model": "gemma-3-12b"}
    },
    "router_prompt": """You are the Semantic Router for an Enterprise AI Gateway.
Analyze the user's message and select the most appropriate AI model.
Options:
1. "OPENAI" - For complex math, logic, or advanced reasoning.
2. "GOOGLE" - For general knowledge, creative writing, or fast responses.
3. "LOCAL" - For simple chitchat, privacy-sensitive data, or offline query.

User Message: "{user_message}"

Respond strictly in valid JSON format: {"target": "MODEL_NAME", "reason": "brief explanation"}"""
}

def load_or_create_config():
    """Auto-generate config file if not exists for plug-and-play setup."""
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False, sort_keys=False)
        logger.info(f"✨ Created default {CONFIG_FILE}. Please fill in your API keys.")
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# =====================================================================
# LOGGING & TELEMETRY (SSE)
# =====================================================================
logging.Formatter.converter = lambda *args: datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).timetuple()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SealAIGateway")

log_clients = set()
TERMINAL_HISTORY = []

async def broadcast_log(msg: str, level: str = "INFO"):
    time_str = datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime("%H:%M:%S")
    log_entry = {"time": time_str, "level": level, "msg": msg}
    TERMINAL_HISTORY.append(log_entry)
    if len(TERMINAL_HISTORY) > 150: TERMINAL_HISTORY.pop(0)
    payload = json.dumps(log_entry)
    for q in list(log_clients):
        try: q.put_nowait(payload)
        except: pass

def log_info(msg): logger.info(msg); asyncio.create_task(broadcast_log(msg, "INFO"))
def log_warning(msg): logger.warning(msg); asyncio.create_task(broadcast_log(msg, "WARN"))
def log_error(msg): logger.error(msg); asyncio.create_task(broadcast_log(msg, "ERROR"))

# =====================================================================
# GLOBAL STATE & DATABASE
# =====================================================================
CONFIG = {}
ROUTER_STATUS = {"active_requests": 0, "endpoints_health": {"router": False, "openai": True, "google": True, "local": False}}
APP_START_TIME = time.time()
FAILED_REQUESTS_LOG = [] 

ANALYTICS = {
    "traffic": {"successful": 0, "failed": 0},
    "tokens": {"google": 0, "openai": 0, "local": 0},
    "performance": {}, # TTFT and TPS metrics
    "routing_dist": {"GOOGLE": 0, "OPENAI": 0, "LOCAL": 0}
}
analytics_lock = asyncio.Lock()
request_lock = asyncio.Lock()

async def init_db():
    async with aiosqlite.connect(SQLITE_DB) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            client_id TEXT, user_name TEXT, target_model TEXT,
            tokens_in INTEGER, tokens_out INTEGER, ttft_ms REAL, total_latency_ms REAL, status_code INTEGER)''')
        await db.commit()
        log_info("🗄️ Telemetry Database Initialized.")

def count_tokens(text: str):
    try: return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except: return len(text) // 4

# =====================================================================
# BACKGROUND WATCHDOG
# =====================================================================
async def health_check():
    """Periodically checks the health of local endpoints."""
    while True:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res_router = await client.get(CONFIG['router_node']['endpoint'].replace("/v1", "/health"))
                ROUTER_STATUS["endpoints_health"]["router"] = (res_router.status_code == 200)
                
                res_worker = await client.get(CONFIG['providers']['local_worker']['endpoint'].replace("/v1", "/health"))
                ROUTER_STATUS["endpoints_health"]["local"] = (res_worker.status_code == 200)
        except:
            ROUTER_STATUS["endpoints_health"]["router"] = False
            ROUTER_STATUS["endpoints_health"]["local"] = False
        await asyncio.sleep(15)

# =====================================================================
# CORE LOGIC: SEMANTIC ROUTER & EXECUTION
# =====================================================================
async def get_routing_decision(user_message: str) -> str:
    """Uses the Local LLM to decide the best provider based on semantics."""
    if not ROUTER_STATUS["endpoints_health"]["router"]:
        log_warning("Router node offline. Fallback to default (GOOGLE).")
        return "GOOGLE"
        
    prompt = CONFIG['router_prompt'].replace("{user_message}", user_message)
    payload = {"model": CONFIG['router_node']['model'], "messages": [{"role": "user", "content": prompt}], "temperature": 0.1}
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.post(f"{CONFIG['router_node']['endpoint']}/chat/completions", json=payload)
            content = res.json()['choices'][0]['message']['content']
            
            # Anti-hallucination JSON parse
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                decision = json.loads(match.group())
                target = decision.get("target", "GOOGLE").upper()
                log_info(f"🧠 Routing Decision: {target} (Reason: {decision.get('reason', 'N/A')})")
                return target if target in ["GOOGLE", "OPENAI", "LOCAL"] else "GOOGLE"
            return "GOOGLE"
    except Exception as e:
        log_error(f"Routing logic failed: {e}")
        return "GOOGLE"

async def execute_provider(target: str, messages: list, stream: bool):
    """Executes the request to the designated AI provider."""
    if target == "OPENAI":
        key = CONFIG['providers']['openai']['api_key']
        model = CONFIG['providers']['openai']['model']
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {key}"}
        payload = {"model": model, "messages": messages, "stream": stream}
        
    elif target == "LOCAL":
        url = f"{CONFIG['providers']['local_worker']['endpoint']}/chat/completions"
        model = CONFIG['providers']['local_worker']['model']
        headers = {"Content-Type": "application/json"}
        payload = {"model": model, "messages": messages, "stream": stream}
        
    else: # GOOGLE
        key = CONFIG['providers']['google']['api_key']
        model = CONFIG['providers']['google']['model']
        method = "streamGenerateContent" if stream else "generateContent"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:{method}?key={key}"
        headers = {"Content-Type": "application/json"}
        
        # Convert to Gemini format
        contents = []
        for m in messages:
            contents.append({"role": "user" if m['role'] == "user" else "model", "parts": [{"text": m['content']}]})
        payload = {"contents": contents}

    client = httpx.AsyncClient(timeout=60.0)
    req = client.build_request("POST", url, json=payload, headers=headers)
    
    if stream:
        res = await client.send(req, stream=True)
        res.raise_for_status()
        return res, model
    else:
        res = await client.send(req)
        res.raise_for_status()
        return res.json(), model

async def stream_transcoder(response: httpx.Response, provider: str, model: str, start_time: float, in_tokens: int, client_id: str, user: str):
    """Universal SSE generator & Analytics recorder."""
    ttft = None
    out_tokens = 0
    try:
        if provider == "GOOGLE":
            buffer = ""
            async for chunk_bytes in response.aiter_bytes():
                try: buffer += chunk_bytes.decode("utf-8")
                except: continue
                while '}' in buffer:
                    try:
                        start_idx = buffer.find('{')
                        if start_idx == -1: buffer = ""; break
                        obj, end_idx = json.JSONDecoder().raw_decode(buffer[start_idx:])
                        buffer = buffer[start_idx + end_idx:]
                        text = obj.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                        if text:
                            if not ttft: ttft = time.time()
                            out_tokens += count_tokens(text)
                            yield f"data: {json.dumps({'id':'cmpl-1','object':'chat.completion.chunk','created':int(time.time()),'model':model,'choices':[{'index':0,'delta':{'content':text}}]})}\n\n"
                    except: break
        else: # OpenAI / Local format
            async for line in response.aiter_lines():
                if line.startswith("data: ") and "[DONE]" not in line:
                    try:
                        chunk = json.loads(line[6:])
                        text = chunk['choices'][0].get('delta', {}).get('content', '')
                        if text:
                            if not ttft: ttft = time.time()
                            out_tokens += count_tokens(text)
                            yield f"{line}\n\n"
                    except: continue
        yield "data: [DONE]\n\n"
    finally:
        # Record Analytics
        end_time = time.time()
        ttft_ms = (ttft - start_time) * 1000 if ttft else 0
        latency_ms = (end_time - start_time) * 1000
        tps = out_tokens / (end_time - ttft) if ttft and end_time > ttft else 0
        
        async with analytics_lock:
            ANALYTICS["traffic"]["successful"] += 1
            ANALYTICS["tokens"][provider.lower()] += (in_tokens + out_tokens)
            perf = ANALYTICS["performance"].setdefault(provider, {"ttft": 0, "tps": 0, "latency": 0, "hits": 0})
            n = perf["hits"]
            perf["ttft"] = round(((perf["ttft"] * n) + ttft_ms) / (n + 1), 2)
            perf["tps"] = round(((perf["tps"] * n) + min(tps, 200)) / (n + 1), 2)
            perf["latency"] = round(((perf["latency"] * n) + latency_ms) / (n + 1), 2)
            perf["hits"] += 1
            
        async with aiosqlite.connect(SQLITE_DB) as db:
            await db.execute("INSERT INTO requests (client_id, user_name, target_model, tokens_in, tokens_out, ttft_ms, total_latency_ms, status_code) VALUES (?,?,?,?,?,?,?,?)",
                             (client_id, user, provider, in_tokens, out_tokens, ttft_ms, latency_ms, 200))
            await db.commit()

# =====================================================================
# FASTAPI ENDPOINTS
# =====================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global CONFIG
    CONFIG = load_or_create_config()
    await init_db()
    asyncio.create_task(health_check())
    log_info("🚀 SealAI Enterprise Router is Online.")
    yield

app = FastAPI(lifespan=lifespan)

class ChatMessage(BaseModel):
    role: str
    content: str
class ChatCompletionRequest(BaseModel):
    messages: List[ChatMessage]
    stream: Optional[bool] = False

@app.get("/")
async def serve_ui(): return FileResponse("index.html")

@app.get("/api/logs")
async def get_logs_history(): return JSONResponse({"logs": TERMINAL_HISTORY})

@app.get("/api/stream_logs")
async def stream_logs(req: Request):
    async def log_gen():
        q = asyncio.Queue(); log_clients.add(q)
        try:
            while True:
                if await req.is_disconnected(): break
                yield f"data: {await q.get()}\n\n"
        finally: log_clients.remove(q)
    return StreamingResponse(log_gen(), media_type="text/event-stream")

@app.get("/api/analytics")
async def get_analytics():
    ANALYTICS["uptime"] = int(time.time() - APP_START_TIME)
    ANALYTICS["active"] = ROUTER_STATUS["active_requests"]
    return JSONResponse({"status": "online", "analytics": ANALYTICS, "health": ROUTER_STATUS["endpoints_health"]})

@app.get("/api/clients")
async def get_clients():
    try:
        async with aiosqlite.connect(SQLITE_DB) as db:
            db.row_factory = aiosqlite.Row
            c = await db.execute("SELECT client_id, COUNT(id) as reqs, SUM(tokens_in+tokens_out) as toks FROM requests GROUP BY client_id ORDER BY toks DESC LIMIT 10")
            u = await db.execute("SELECT user_name, COUNT(id) as reqs, SUM(tokens_in+tokens_out) as toks FROM requests GROUP BY user_name ORDER BY toks DESC LIMIT 20")
            return JSONResponse({"clients": [dict(r) for r in await c.fetchall()], "users": [dict(r) for r in await u.fetchall()]})
    except: return JSONResponse({"error": "DB Error"})

@app.get("/api/errors")
async def get_errors(): return JSONResponse({"logs": FAILED_REQUESTS_LOG})

@app.post("/v1/chat/completions")
async def handle_chat(request: ChatCompletionRequest, raw_req: Request):
    if raw_req.headers.get("Authorization") != f"Bearer {CONFIG['server']['api_key']}":
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    client_id = raw_req.headers.get("X-Client-ID", "Web-UI")
    user_name = raw_req.headers.get("X-User-Name", "Anonymous")
    
    async with request_lock: ROUTER_STATUS["active_requests"] += 1
    start_time = time.time()
    
    try:
        msg_dicts = [m.dict() for m in request.messages]
        in_text = " ".join([m['content'] for m in msg_dicts])
        in_tokens = count_tokens(in_text)
        
        # 1. AI Decision Making
        target = await get_routing_decision(msg_dicts[-1]['content'][:1000])
        async with analytics_lock: ANALYTICS["routing_dist"][target] += 1
        
        # 2. Execution
        res, model_name = await execute_provider(target, msg_dicts, request.stream)
        
        if request.stream:
            return StreamingResponse(stream_transcoder(res, target, model_name, start_time, in_tokens, client_id, user_name), media_type="text/event-stream")
        else:
            async with analytics_lock: ANALYTICS["traffic"]["successful"] += 1
            return res

    except Exception as e:
        log_error(f"Request failed: {e}")
        FAILED_REQUESTS_LOG.insert(0, {"time": datetime.now().strftime("%H:%M:%S"), "client": client_id, "error": str(e), "payload": in_text[:200] + "..."})
        if len(FAILED_REQUESTS_LOG) > 10: FAILED_REQUESTS_LOG.pop()
        async with analytics_lock: ANALYTICS["traffic"]["failed"] += 1
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        async with request_lock: ROUTER_STATUS["active_requests"] -= 1

if __name__ == "__main__":
    config = load_or_create_config()
    uvicorn.run("router:app", host="0.0.0.0", port=config['server']['port'])
