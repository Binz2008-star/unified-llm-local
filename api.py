"""
FastAPI for Second Brain v4 - API + Web UI backend
Endpoints (all mounted under APIRouter(prefix="/api")):
  POST /api/search - hybrid search
  POST /api/chat - chat with context (language-aware: en/ar)
  POST /api/agent - multi-agent task
  GET  /api/agent/stream - SSE stream for agent progress
  GET  /api/status - health
  GET  /api/memory - list memories
  POST /api/memory - add memory
  GET  /api/projects - list projects
  GET  /api/system - system telemetry (CPU, memory, disk)
  POST /api/system/benchmark-results - store benchmark metrics
  GET  /api/system/metrics - benchmark telemetry
  GET  /data.json - raw telemetry file
  GET  / - Web UI

Language & Emotional Intent Router:
  detect_intent(req) FastAPI dependency inspects JSON payload (query/message/task),
  detects Arabic vs English and emotional tone, returns
  {"lang": "ar"|"en", "emotion": str, "raw_text": str}.
"""
import os
import asyncio
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional, AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, APIRouter, Depends
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import asyncpg
import aiohttp
import psutil

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

try:
    import sys

    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "v4-extract" / "second-brain-v4"))
except Exception:
    pass

from brain_agent_v4 import (
    search_brain,
    PROJECTS,
    CURRENT_PROJECT,
    embed,
    run_multi_agent_stream,
    close_pool,
)

# Data.json path (from ai-dashboard)
DATA_JSON_PATH = Path(os.getenv("DATA_JSON_PATH", str(ROOT / "ai-dashboard" / "data.json")))

# ---------------------------------------------------------------------------
# Environment configuration
# ---------------------------------------------------------------------------
NEON_DSN = os.getenv("NEON_DSN") or os.getenv("DATABASE_URL")
OLLAMA_EMBED_URL = os.getenv("OLLAMA_EMBED_URL", "http://127.0.0.1:11434/api/embed")
OLLAMA_CHAT_URL = os.getenv("OLLAMA_CHAT_URL", "http://127.0.0.1:11434/api/chat")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
CHAT_MODEL = os.getenv("CHAT_MODEL", "deepseek-r1:14b")

ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "*").split(",")
    if o.strip()
] or ["*"]

# ---------------------------------------------------------------------------
# Lifespan: shared aiohttp session + DB pool lifecycle
# ---------------------------------------------------------------------------
_lifespan_session: Optional[aiohttp.ClientSession] = None
_pool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _lifespan_session
    # Startup
    _lifespan_session = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=180, connect=30)
    )
    try:
        yield
    finally:
        # Shutdown
        if _lifespan_session is not None:
            await _lifespan_session.close()
            _lifespan_session = None
        await close_pool()


app = FastAPI(title="Second Brain v4", version="4.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(NEON_DSN, min_size=1, max_size=4, command_timeout=120)
    return _pool


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class SearchRequest(BaseModel):
    query: str
    top_k: int = 8


class ChatRequest(BaseModel):
    query: str
    top_k: int = 6


class AgentRequest(BaseModel):
    task: str
    project: Optional[str] = None


class MemoryRequest(BaseModel):
    type: str = "fact"
    content: str
    project_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Language & Emotional Intent Router (FastAPI dependency)
# ---------------------------------------------------------------------------
ARABIC_UNICODE_MIN = 0x0600
ARABIC_UNICODE_MAX = 0x06FF

EMOTION_KEYWORDS = {
    "urgency": [
        "asap", "urgent", "immediately", "hurry", "quick", "now",
        "عاجل", "فورا", "بسرعة", "ضروري", "مستعجل",
    ],
    "frustration": [
        "annoying", "frustrated", "frustrating", "stupid", "broken",
        "not working", "fix this", "worst", "hate",
        "مزعج", "سيء", "معطل", "خاطئ", "غاضب", "منزعج", "لا يعمل",
    ],
    "satisfaction": [
        "great", "awesome", "excellent", "perfect", "wonderful", "love it",
        "ممتاز", "رائع", "مثالي", "أحسنت",
    ],
    "confusion": [
        "confused", "unclear", "not sure", "what do you mean", "huh",
        "مش فاهم", "غير واضح", "لا أفهم", "مش واضح",
    ],
}

DEFAULT_EMOTION = "neutral"


def detect_lang(text: str) -> str:
    """Return 'ar' if any Arabic Unicode character is present, else 'en'."""
    for ch in text:
        if ARABIC_UNICODE_MIN <= ord(ch) <= ARABIC_UNICODE_MAX:
            return "ar"
    return "en"


def detect_emotion(text: str) -> str:
    """Scan lowercased text for common emotional indicator keywords."""
    lowered = text.lower()
    for emotion, keywords in EMOTION_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            return emotion
    return DEFAULT_EMOTION


async def detect_intent(req: Request) -> dict:
    """FastAPI dependency: inspect JSON payload (query/message/task) -> intent dict."""
    raw_text = ""
    try:
        body = await req.json()
    except Exception:
        body = {}

    if isinstance(body, dict):
        for key in ("query", "message", "task"):
            value = body.get(key)
            if isinstance(value, str) and value.strip():
                raw_text = value
                break

    # Fallback for GET/query-string endpoints (e.g. /api/agent/stream?task=...)
    if not raw_text:
        qp = req.query_params.get("task") or req.query_params.get("query") or ""
        if qp.strip():
            raw_text = qp

    return {
        "lang": detect_lang(raw_text),
        "emotion": detect_emotion(raw_text),
        "raw_text": raw_text,
    }


# Localized messages by language
LANG_MESSAGES = {
    "en": {
        "search_unavailable": "search backend unavailable",
        "chat_timeout": "chat timed out after 3 attempts",
        "chat_error_prefix": "chat error: ",
        "no_answer": "No answer returned by the model.",
        "fast_mode": "Found {n} relevant chunks. Use a question for LLM analysis.",
        "agent_completed": "Agent task completed.",
        "agent_error": "Agent execution failed: {err}",
        "memory_added": "added",
    },
    "ar": {
        "search_unavailable": "خدمة البحث غير متاحة حالياً",
        "chat_timeout": "انتهت مهلة الدردشة بعد 3 محاولات",
        "chat_error_prefix": "خطأ في الدردشة: ",
        "no_answer": "لم يُعد النموذج أي إجابة.",
        "fast_mode": "تم العثور على {n} مقطعاً ذا صلة. اطرح سؤالاً للتحليل الذكي.",
        "agent_completed": "اكتملت مهمة الوكيل بنجاح.",
        "agent_error": "فشل تنفيذ الوكيل: {err}",
        "memory_added": "أُضيف",
    },
}


def l10n(lang: str, key: str, **kwargs) -> str:
    msg = LANG_MESSAGES.get(lang, LANG_MESSAGES["en"]).get(key, LANG_MESSAGES["en"].get(key, ""))
    if kwargs:
        return msg.format(**kwargs)
    return msg


# ---------------------------------------------------------------------------
# Shared HTTP helper: post JSON to Ollama with the shared lifespan session
# ---------------------------------------------------------------------------
async def _ollama_chat(messages: list) -> tuple:
    """POST to Ollama chat with retries. Returns (ok: bool, payload: dict)."""
    session = _lifespan_session
    own = False
    if session is None:
        session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=180, connect=30))
        own = True
    try:
        for attempt in range(3):
            try:
                async with session.post(
                    OLLAMA_CHAT_URL,
                    json={"model": CHAT_MODEL, "messages": messages, "stream": False},
                    timeout=aiohttp.ClientTimeout(total=180, connect=30),
                ) as resp:
                    data = await resp.json()
                return True, data
            except (aiohttp.TimeoutError, aiohttp.ClientError):
                if attempt == 2:
                    return False, {}
                await asyncio.sleep(1)
        return False, {}
    finally:
        if own:
            await session.close()


# ---------------------------------------------------------------------------
# APIRouter (prefix="/api")
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/api")


@router.post("/search")
async def api_search(req: SearchRequest):
    if not search_brain:
        raise HTTPException(503, "search backend unavailable")
    results = await search_brain(req.query, top_k=req.top_k)
    return {
        "query": req.query,
        "results": [
            {
                "project": r["project_id"],
                "file": r["file_path"],
                "chunk": r.get("chunk_name"),
                "content": r["content"][:1000],
                "score": float(r.get("similarity", r.get("rank", 0))),
            }
            for r in results
        ],
    }


@router.post("/chat")
async def api_chat(req: ChatRequest, intent: dict = Depends(detect_intent)):
    results = await search_brain(req.query, top_k=min(req.top_k, 4)) if search_brain else []
    context = "\n\n".join(f"[{r['project_id']}/{r['file_path']}] {r['content'][:800]}" for r in results)

    lang = intent["lang"]

    # Fast mode: if query is short, just return search results
    if len(req.query.split()) <= 3 and not req.query.endswith('?'):
        return {
            "query": req.query,
            "answer": l10n(lang, "fast_mode", n=len(results)),
            "context_used": len(results),
            "fast_mode": True,
            "lang": lang,
            "emotion": intent["emotion"],
            "results": [
                {"project": r["project_id"], "file": r["file_path"], "chunk": r.get("chunk_name"),
                 "content": r["content"][:500], "score": float(r.get("similarity", r.get("rank", 0)))}
                for r in results
            ],
        }

    system = "Answer concisely using the provided code context. Max 3 sentences."
    if lang == "ar":
        system = "أجب بإيجاز باستخدام سياق الكود المقدم. بأقصى 3 جمل."

    user_prompt = f"Context:\n{context}\n\nQuestion: {req.query}"
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user_prompt}]

    ok, data = await _ollama_chat(messages)
    if not ok:
        return {
            "query": req.query,
            "error": l10n(lang, "chat_timeout"),
            "context_used": len(results),
            "lang": lang,
            "emotion": intent["emotion"],
        }
    if "error" in data:
        return {
            "query": req.query,
            "error": l10n(lang, "chat_error_prefix") + str(data["error"]),
            "context_used": len(results),
            "lang": lang,
            "emotion": intent["emotion"],
        }

    answer = data.get("message", {}).get("content")
    if not answer:
        answer = l10n(lang, "no_answer")

    return {
        "query": req.query,
        "answer": answer,
        "context_used": len(results),
        "lang": lang,
        "emotion": intent["emotion"],
    }


@router.post("/agent")
async def api_agent(req: AgentRequest, intent: dict = Depends(detect_intent)):
    from brain_agent_v4 import run_multi_agent

    lang = intent["lang"]
    try:
        result = await run_multi_agent(req.task)
    except Exception as e:
        raise HTTPException(500, l10n(lang, "agent_error", err=str(e)))
    return {"status": "completed", "task": req.task, "lang": lang, "result": result}


@router.get("/agent/stream")
async def api_agent_stream(task: str):
    """Stream agent progress via Server-Sent Events"""
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for event in run_multi_agent_stream(task):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        yield f"data: {json.dumps({'type': 'complete', 'task': task})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/status")
async def status():
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            cnt = await conn.fetchval("SELECT COUNT(*) FROM chunks_v4")
            projs = await conn.fetch("SELECT project_id, COUNT(*) as c FROM chunks_v4 GROUP BY project_id")
            try:
                mem = await conn.fetchval("SELECT COUNT(*) FROM memory")
            except Exception:
                mem = 0
            try:
                graph = await conn.fetchval("SELECT COUNT(*) FROM code_graph")
            except Exception:
                graph = 0
        return {
            "status": "ok",
            "chunks_v4": cnt,
            "memory": mem,
            "code_graph": graph,
            "projects": {r["project_id"]: r["c"] for r in projs},
            "model": CHAT_MODEL,
            "embed_model": EMBED_MODEL,
            "current_project": CURRENT_PROJECT,
            "project_roots": {k: str(v) for k, v in PROJECTS.items()},
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/projects")
async def api_projects():
    return {"current": CURRENT_PROJECT, "projects": {k: str(v) for k, v in PROJECTS.items()}}


@router.get("/memory")
async def api_memory_list(limit: int = 50):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, type, content, project_id, created_at FROM memory ORDER BY id DESC LIMIT $1", limit
        )
    return {"memories": [dict(r) for r in rows]}


@router.post("/memory")
async def api_memory_add(req: MemoryRequest):
    proj = req.project_id or CURRENT_PROJECT
    emb = await embed(req.content[:500])
    emb_str = "[" + ",".join(f"{x:.6f}" for x in emb) + "]"
    pool = await get_pool()
    async with pool.acquire() as conn:
        mid = await conn.fetchval(
            "INSERT INTO memory (type, content, project_id, embedding) VALUES ($1,$2,$3,$4::vector) RETURNING id",
            req.type, req.content, proj, emb_str,
        )
    return {"id": mid, "status": "added", "type": req.type, "project_id": proj}


@router.get("/system")
async def api_system():
    """System telemetry: CPU, memory, disk - reads from data.json or live psutil"""
    try:
        start = time.time()

        # Try reading from data.json first (updated by external collector)
        if DATA_JSON_PATH.exists():
            try:
                with open(DATA_JSON_PATH, 'r') as f:
                    data = json.load(f)
                cpu_cores = data.get("cpu_cores", [])
                cpu_total = data.get("cpu", 0)
                if not cpu_total and cpu_cores:
                    cpu_total = sum(cpu_cores) / len(cpu_cores)

                mem = data.get("mem", {})
                disk = data.get("disk", {})

                result = {
                    "cpu": {
                        "total_percent": cpu_total,
                        "per_core_percent": cpu_cores,
                        "core_count": len(cpu_cores) if cpu_cores else psutil.cpu_count(logical=True),
                        "cpu_freq": data.get("cpu_freq", "3.4 GHz"),
                    },
                    "memory": {
                        "total_bytes": int((mem.get("total", 16) or 16) * 1024**3),
                        "available_bytes": int((mem.get("free", 1) or 1) * 1024**3),
                        "used_bytes": int((mem.get("used", 15) or 15) * 1024**3),
                        "percent": mem.get("percent", 0),
                    },
                    "disk": {
                        "total_bytes": int((disk.get("total", 446) or 446) * 1024**3),
                        "used_bytes": int((disk.get("used", 361) or 361) * 1024**3),
                        "free_bytes": int((disk.get("free", 85) or 85) * 1024**3),
                        "percent": disk.get("usePct", 0),
                    },
                    "elapsed_ms": int((time.time() - start) * 1000),
                }
                return result
            except Exception:
                pass  # Fall through to live psutil

        # Fallback: live psutil measurement (non-blocking async sleep)
        psutil.cpu_percent(interval=None, percpu=True)
        await asyncio.sleep(0.1)
        cpu_percent_per_core = psutil.cpu_percent(interval=None, percpu=True)
        cpu_total = psutil.cpu_percent(interval=None)

        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        result = {
            "cpu": {
                "total_percent": cpu_total,
                "per_core_percent": cpu_percent_per_core,
                "core_count": psutil.cpu_count(logical=True),
            },
            "memory": {
                "total_bytes": memory.total,
                "available_bytes": memory.available,
                "used_bytes": memory.used,
                "percent": memory.percent,
            },
            "disk": {
                "total_bytes": disk.total,
                "used_bytes": disk.used,
                "free_bytes": disk.free,
                "percent": (disk.used / disk.total) * 100,
            },
            "elapsed_ms": int((time.time() - start) * 1000),
        }
        return result
    except Exception as e:
        import traceback

        return {"error": str(e), "trace": traceback.format_exc()}


# Benchmark metrics storage (in-memory, persisted via API)
benchmark_metrics = {
    "avg_ttft_ms": 0.0,
    "avg_tps": 0.0,
    "p95_ttft_ms": 0.0,
    "total_requests": 0,
    "success_rate": 100.0,
    "updated_at": "N/A",
}


@router.post("/system/benchmark-results")
async def update_benchmark_results(metrics: dict):
    """Receive benchmark results from benchmark_suite.py"""
    global benchmark_metrics
    benchmark_metrics = metrics
    return {"status": "ok"}


@router.get("/system/metrics")
async def get_system_metrics():
    """Get latest benchmark telemetry"""
    return benchmark_metrics


app.include_router(router)


# ---------------------------------------------------------------------------
# Non-API routes: root UI + raw telemetry file
# ---------------------------------------------------------------------------
@app.get("/data.json")
async def get_data_json():
    """Serve the data.json file from ai-dashboard"""
    if DATA_JSON_PATH.exists():
        return JSONResponse(content=json.loads(DATA_JSON_PATH.read_text()))
    return {"error": "data.json not found", "path": str(DATA_JSON_PATH)}


@app.get("/", response_class=HTMLResponse)
async def ui():
    html_path = ROOT / "ui" / "index.html"
    if html_path.exists():
        return html_path.read_text(encoding='utf-8')
    return """
    <html><body style="font-family: monospace; padding: 20px;">
    <h1>🧠 Second Brain v4 API</h1>
    <p>API running. Create ui/index.html for the web UI.</p>
    <ul>
      <li>POST /api/search - search brain</li>
      <li>POST /api/chat - chat with context</li>
      <li>POST /api/agent - multi-agent task</li>
      <li>GET /api/status</li>
      <li>GET /api/memory</li>
      <li>POST /api/memory</li>
    </ul>
    <input id="q" placeholder="search brain..." style="width:400px"><button onclick="search()">Search</button>
    <pre id="results"></pre>
    <script>
      async function search() {
        const res = await fetch('/api/search', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({query:document.getElementById('q').value, top_k:8})});
        const data = await res.json();
        document.getElementById('results').textContent = JSON.stringify(data, null, 2);
      }
    </script>
    </body></html>
    """


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
