import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
import httpx
import yaml
import json
import logging
import asyncio
from datetime import datetime
import pytz
import re

# =====================================================================
# SYSTEM INITIALIZATION & LOGGING
# =====================================================================
logging.Formatter.converter = lambda *args: datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).timetuple()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [SEAL-ROUTER] - %(levelname)s - %(message)s')
logger = logging.getLogger("SealAI")

def load_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

CONFIG = load_config()
TERMINAL_HISTORY = []
log_clients = set()
STATS = {
    "requests": 0, "fallback_triggered": 0,
    "routed_to": {"EASY_LOCAL": 0, "MEDIUM_GEMINI": 0, "HARD_OPENAI": 0}
}

app = FastAPI(title="SealAI™ Edge-Cloud Router")

# --- REALTIME LOGGING FOR DASHBOARD ---
async def broadcast_log(msg: str, level: str = "INFO"):
    time_str = datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime("%H:%M:%S")
    log_entry = {"time": time_str, "level": level, "msg": msg}
    TERMINAL_HISTORY.append(log_entry)
    if len(TERMINAL_HISTORY) > 50: TERMINAL_HISTORY.pop(0)
    for q in list(log_clients):
        try: q.put_nowait(json.dumps(log_entry))
        except: pass

def log_sys(msg, level="INFO"): 
    if level == "INFO": logger.info(msg)
    elif level == "WARN": logger.warning(msg)
    else: logger.error(msg)
    asyncio.create_task(broadcast_log(msg, level))

# =====================================================================
# CORE LLM ROUTING ENGINE
# =====================================================================
async def evaluate_complexity_with_llm(user_query: str) -> str:
    """
    Uses the Local Edge Node (Gemma) to evaluate query complexity.
    Returns: "EASY", "MEDIUM", or "HARD".
    """
    log_sys(f"🧠 Analyzing cognitive load for query: {user_query[:50]}...", "INFO")
    
    system_prompt = CONFIG['routing_engine']['eval_prompt']
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query}
    ]
    
    payload = {
        "model": CONFIG['edge_node']['name'],
        "messages": messages,
        "temperature": 0.1, # Low temp for deterministic routing output
        "max_tokens": 50
    }
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{CONFIG['edge_node']['endpoint']}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            resp.raise_for_status()
            content = resp.json()['choices'][0]['message']['content']
            
            # Extract JSON from potential markdown blocks
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                decision = json.loads(json_match.group())
                difficulty = decision.get("difficulty", "MEDIUM").upper()
                reason = decision.get("reason", "No reason provided")
                log_sys(f"🎯 Routing Decision: {difficulty} (Reason: {reason})", "INFO")
                return difficulty if difficulty in ["EASY", "MEDIUM", "HARD"] else "MEDIUM"
            
    except Exception as e:
        log_sys(f"⚠️ Router Evaluation Timeout/Error: {e}. Defaulting to MEDIUM.", "WARN")
        return "MEDIUM"

# =====================================================================
# PROVIDER INTEGRATION & FALLBACK PROTOCOLS
# =====================================================================
async def call_openai(messages: list, is_hard: bool = False):
    log_sys("☁️ Executing via OpenAI (Heavy Reasoning Mode)..." if is_hard else "☁️ Executing via OpenAI...", "INFO")
    payload = {
        "model": CONFIG['cloud_providers']['openai']['model'],
        "messages": messages,
    }
    # If the router determined this is a HARD math/logic problem, trigger OpenAI's high reasoning effort
    if is_hard: payload["reasoning_effort"] = "high"

    async with httpx.AsyncClient(timeout=CONFIG['cloud_providers']['openai']['timeout_sec']) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {CONFIG['cloud_providers']['openai']['api_key']}"}
        )
        resp.raise_for_status()
        return resp.json()

async def call_gemini(messages: list):
    log_sys("⚡ Executing via Google Gemini (Medium Workload)...", "INFO")
    gemini_model = CONFIG['cloud_providers']['google']['model']
    api_key = CONFIG['cloud_providers']['google']['api_key']
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={api_key}"
    
    # Transform OpenAI message format to Gemini format
    gemini_contents = []
    for m in messages:
        role = "user" if m['role'] == "user" else "model"
        gemini_contents.append({"role": role, "parts": [{"text": str(m['content'])}]})
        
    async with httpx.AsyncClient(timeout=CONFIG['cloud_providers']['google']['timeout_sec']) as client:
        resp = await client.post(url, json={"contents": gemini_contents})
        resp.raise_for_status()
        
        # Transform response back to OpenAI format for seamless client integration
        text_content = resp.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
        return {
            "model": gemini_model,
            "choices": [{"message": {"role": "assistant", "content": text_content}}]
        }

async def call_local_edge(messages: list):
    log_sys("🔒 Executing securely via InsightBox Edge Node (Zero-Cost)...", "INFO")
    payload = {"model": CONFIG['edge_node']['name'], "messages": messages}
    async with httpx.AsyncClient(timeout=CONFIG['edge_node']['timeout_sec']) as client:
        resp = await client.post(
            f"{CONFIG['edge_node']['endpoint']}/chat/completions",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        resp.raise_for_status()
        return resp.json()

# =====================================================================
# API ENDPOINTS
# =====================================================================
class ChatRequest(BaseModel):
    messages: List[Dict[str, Any]]

@app.get("/")
async def serve_dashboard(): return FileResponse("index.html")

@app.get("/api/stream_logs")
async def stream_logs(req: Request):
    async def log_generator():
        q = asyncio.Queue()
        log_clients.add(q)
        try:
            while True:
                if await req.is_disconnected(): break
                msg = await q.get()
                yield f"data: {msg}\n\n"
        finally: log_clients.remove(q)
    return StreamingResponse(log_generator(), media_type="text/event-stream")

@app.get("/api/analytics/overview")
async def get_overview():
    return JSONResponse({
        "status": "online",
        "analytics": {
            "server_uptime_sec": 3600,
            "traffic": {"successful_requests": STATS["requests"], "failed_requests": 0},
            "economy": {"shadow_billing_usd": STATS["routed_to"]["EASY_LOCAL"] * 0.05, "freeloader_index_pct": 0},
            "performance": {
                "Edge_Gemma_3": {"hits": STATS["routed_to"]["EASY_LOCAL"], "tps_avg": 45, "latency_ms_avg": 250},
                "Cloud_Gemini": {"hits": STATS["routed_to"]["MEDIUM_GEMINI"], "tps_avg": 80, "latency_ms_avg": 600},
                "Cloud_OpenAI": {"hits": STATS["routed_to"]["HARD_OPENAI"], "tps_avg": 60, "latency_ms_avg": 1200}
            },
            "fallback_depth": [0, STATS["fallback_triggered"], 0, 0, 0]
        },
        "quota_usage": {"google": {}, "openai": {}},
        "local_health": {"active_requests": 1, "local_12b_alive": True}
    })

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest, raw_req: Request):
    auth_header = raw_req.headers.get("Authorization")
    if not auth_header or auth_header.split(" ")[1] != CONFIG['server']['api_key']: 
        raise HTTPException(status_code=401, detail="Unauthorized")

    messages = request.messages
    # Get the last user message to evaluate
    last_user_msg = next((m['content'] for m in reversed(messages) if m['role'] == 'user'), "")
    
    difficulty = await evaluate_complexity_with_llm(str(last_user_msg))
    STATS["requests"] += 1
    
    # DEFINE FALLBACK CHAIN BASED ON DIFFICULTY
    if difficulty == "HARD":
        STATS["routed_to"]["HARD_OPENAI"] += 1
        execution_chain = [
            ("OPENAI", lambda: call_openai(messages, is_hard=True)),
            ("GEMINI", lambda: call_gemini(messages)),
            ("LOCAL", lambda: call_local_edge(messages))
        ]
    elif difficulty == "MEDIUM":
        STATS["routed_to"]["MEDIUM_GEMINI"] += 1
        execution_chain = [
            ("GEMINI", lambda: call_gemini(messages)),
            ("OPENAI", lambda: call_openai(messages, is_hard=False)),
            ("LOCAL", lambda: call_local_edge(messages))
        ]
    else: # EASY
        STATS["routed_to"]["EASY_LOCAL"] += 1
        execution_chain = [
            ("LOCAL", lambda: call_local_edge(messages)),
            ("GEMINI", lambda: call_gemini(messages))
        ]

    # EXECUTE WITH SMART FALLBACK
    for idx, (provider_name, executor) in enumerate(execution_chain):
        try:
            return await executor()
        except Exception as e:
            log_sys(f"❌ {provider_name} Failed: {str(e)}", "ERROR")
            if idx < len(execution_chain) - 1:
                STATS["fallback_triggered"] += 1
                next_provider = execution_chain[idx+1][0]
                log_sys(f"🚑 Fallback Protocol Activated! Rerouting to {next_provider}...", "WARN")
            else:
                log_sys("💀 All Providers Exhausted. Knowledge pipeline broken.", "ERROR")
                raise HTTPException(status_code=500, detail="InsightBox Pipeline Failure")

if __name__ == "__main__":
    port = CONFIG.get("server", {}).get("port", 6767)
    log_sys(f"🚀 InsightBox Enterprise Router initializing on port {port}...", "INFO")
    uvicorn.run("router:app", host="0.0.0.0", port=port)
