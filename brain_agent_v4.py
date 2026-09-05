#!/usr/bin/env python3
"""
🧠 SECOND BRAIN v4 - Multi-Agent System with Memory & Self-Evolution
"""
import asyncio
import os
import sys
import json
import uuid
import subprocess
import shlex
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
from dotenv import load_dotenv
import asyncpg
import aiohttp

# Gemini integration
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Structured logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("SecondBrain")

# Security: Shell command denylist
SHELL_DENYLIST = (
    "rm -rf /", "rm -rf ~", "rm -rf .", ":(){:|:&};:",
    "git push", "git reset --hard", "git clean -fd",
    "> /dev/sd", "mkfs", "dd if=", "shutdown", "reboot",
)

class GeminiLLMClient:
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            logger.error("❌ GEMINI_API_KEY environment variable is not set!")
            raise ValueError("GEMINI_API_KEY is missing. Please set it in your environment.")

        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name
        logger.info(f"✨ Gemini LLM Client initialized successfully with model: {self.model_name}")

    async def generate_response(self, prompt: str, system_instruction: str = None) -> str:
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction
            ) if system_instruction else None

            chat = self.client.chats.create(
                model=self.model_name,
                config=config
            )
            response = chat.send_message(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return f"Error executing LLM call: {str(e)}"

llm_client = None
if GEMINI_AVAILABLE:
    try:
        llm_client = GeminiLLMClient()
    except Exception as e:
        logger.warning(f"Gemini client initialization failed: {e}")

def tool_gemini_query(prompt: str) -> str:
    if not llm_client:
        return "Gemini client not available (check GEMINI_API_KEY and google-genai installation)"
    try:
        chat = llm_client.client.chats.create(model="gemini-1.5-flash")
        res = chat.send_message(prompt)
        return res.text
    except Exception as e:
        return f"Gemini Query Failed: {str(e)}"

KB_ROOT = Path(__file__).parent
load_dotenv(KB_ROOT / ".env")

NEON_DSN = os.getenv("NEON_DSN") or os.getenv("DATABASE_URL")
OLLAMA_EMBED_URL = os.getenv("OLLAMA_EMBED_URL", "http://127.0.0.1:11434/api/embed")
OLLAMA_CHAT_URL = os.getenv("OLLAMA_CHAT_URL", "http://127.0.0.1:11434/api/chat")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
ARCHITECT_MODEL = os.getenv("ARCHITECT_MODEL", "deepseek-r1:14b")
EDITOR_MODEL = os.getenv("EDITOR_MODEL", "deepseek-r1:14b")
EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))
AUTO_COMMIT = os.getenv("AUTO_COMMIT", "false").strip().lower() == "true"

def resolve_proj(env_key, fallbacks):
    v = os.getenv(env_key)
    if v and Path(v).exists():
        return v
    for p in fallbacks:
        if Path(p).exists():
            return p
    return fallbacks[0] if fallbacks else None

PROJECTS = {
    "content-engine": resolve_proj("PROJECT_CONTENT_ENGINE", [r"X:\content engine\Robin-Content-Engine-v2"]),
    "lvyy": resolve_proj("PROJECT_LVYY", [r"C:\Users\loyal\lvyy-ai-sales-agent"]),
    "rico": resolve_proj("PROJECT_RICO", [r"X:\rico\Rico-Your-AI-intelligent-job-hunt-partner-in-the-UAE"]),
    "second-brain": str(KB_ROOT),
}
PROJECTS = {k: v for k, v in PROJECTS.items() if v and Path(v).exists()}
CURRENT_PROJECT = os.getenv("CURRENT_PROJECT", "lvyy" if "lvyy" in PROJECTS else list(PROJECTS.keys())[0] if PROJECTS else None)

sys.path.insert(0, str(KB_ROOT / "v4-extract" / "second-brain-v4"))
sys.path.insert(0, str(KB_ROOT))
memory_mgr = None
_pool = None

async def _get_pool():
    global _pool, memory_mgr
    if _pool is None and NEON_DSN:
        _pool = await asyncpg.create_pool(NEON_DSN, min_size=1, max_size=4, command_timeout=120)
        if memory_mgr and memory_mgr.pool is None:
            memory_mgr.pool = _pool
    return _pool

async def close_pool():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None

try:
    from memory import MemoryManager
    def _on_memory_reload(name, path):
        print(f"[Memory] Reloaded {name} from {path}")
    memory_mgr = MemoryManager(memory_dir=str(KB_ROOT / "memory"), on_reload=_on_memory_reload)
except Exception as e:
    print(f"[memory] disabled: {e}")

async def embed(text: str) -> List[float]:
    if not text or not text.strip():
        return [0.0] * EMBED_DIM
    async with aiohttp.ClientSession() as session:
        for _ in range(3):
            try:
                async with session.post(OLLAMA_EMBED_URL, json={"model": EMBED_MODEL, "input": text}) as resp:
                    data = await resp.json()
                    return data["embeddings"][0]
            except Exception:
                await asyncio.sleep(1)
    raise RuntimeError("embed failed")

async def search_brain(query: str, top_k: int = 4) -> List[Dict]:
    if not memory_mgr:
        logger.warning("MemoryManager not initialized, returning empty results")
        return []

    try:
        query_embedding = await embed(query)
        emb_str = "[" + ",".join(f"{x:.6f}" for x in query_embedding) + "]"
        pool = await _get_pool()
        if not pool:
            return []
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT project_id, file_path, content
                   FROM chunks_v4
                   ORDER BY embedding <=> $1::vector
                   LIMIT $2""",
                emb_str, top_k
            )
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"search_brain error: {e}")
        return []

def _jsonable(value):
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)

async def save_conversation(session_id: str, role: str, content: str, tool_calls=None, project_id: Optional[str] = None):
    payload = json.dumps(_jsonable(tool_calls)) if tool_calls else None
    pool = await _get_pool()
    if not pool:
        return
    for attempt in range(3):
        try:
            async with pool.acquire() as conn:
                if payload:
                    await conn.execute(
                        "INSERT INTO conversations (session_id, role, content, tool_calls, project_id) VALUES ($1,$2,$3,$4::jsonb,$5)",
                        session_id, role, content, payload, project_id,
                    )
                else:
                    await conn.execute(
                        "INSERT INTO conversations (session_id, role, content, project_id) VALUES ($1,$2,$3,$4)",
                        session_id, role, content, project_id,
                    )
            return
        except Exception:
            await asyncio.sleep(0.5 * (attempt + 1))

async def persist_agent_history(session_id: str, agents: List[Any]) -> int:
    saved = 0
    for agent in agents:
        for msg in agent.history:
            role = msg.get("role")
            if role not in ("user", "assistant", "tool"):
                continue
            content = msg.get("content")
            content = content if isinstance(content, str) else str(content or "")
            tool_calls = msg.get("tool_calls")
            await save_conversation(session_id, role, content, tool_calls, CURRENT_PROJECT)
            saved += 1
    return saved

class Agent:
    def __init__(self, name: str, model: str, system_prompt: str):
        self.name = name
        self.model = model
        self.system = system_prompt
        self.history = []

    async def chat(self, user_msg: str, tools=None, tool_map=None):
        self.history.append({"role": "user", "content": user_msg})
        messages = [{"role": "system", "content": self.system}] + self.history

        async with aiohttp.ClientSession() as session:
            for _ in range(8):
                payload = {"model": self.model, "messages": messages, "stream": False}
                if tools:
                    payload["tools"] = tools

                try:
                    async with session.post(OLLAMA_CHAT_URL, json=payload,
                                            timeout=aiohttp.ClientTimeout(total=600, connect=60)) as resp:
                        data = await resp.json()
                except (aiohttp.TimeoutError, aiohttp.ClientError):
                    await asyncio.sleep(2)
                    continue
                if "error" in data:
                    return f"ERROR: {data['error']}"
                msg = data["message"]

                if not msg.get("tool_calls"):
                    self.history.append(msg)
                    return msg.get("content", "")

                messages.append(msg)
                self.history.append(msg)
                for tc in msg["tool_calls"]:
                    fname = tc["function"]["name"]
                    args = tc["function"].get("arguments", {})
                    args = args if isinstance(args, dict) else json.loads(args or "{}")
                    func = tool_map.get(fname) if tool_map else None
                    result = "Tool not found"
                    if func:
                        try:
                            result = await func(**args) if asyncio.iscoroutinefunction(func) else func(**args)
                        except Exception as e:
                            result = f"Error: {e}"
                    tool_msg = {"role": "tool", "name": fname, "args": args, "content": str(result)[:8000]}
                    messages.append(tool_msg)
                    self.history.append(tool_msg)

        return "Max tool loops reached"

def tool_list_projects():
    return json.dumps(PROJECTS, indent=2)

def tool_switch_project(project_id: str):
    global CURRENT_PROJECT
    if project_id not in PROJECTS:
        return f"Not found. Available: {list(PROJECTS.keys())}"
    CURRENT_PROJECT = project_id
    os.chdir(PROJECTS[project_id])
    env_path = KB_ROOT / ".env"
    if env_path.exists():
        content = env_path.read_text()
        import re
        if "CURRENT_PROJECT" in content:
            content = re.sub(r"CURRENT_PROJECT=.*", f"CURRENT_PROJECT={project_id}", content, flags=re.M)
        else:
            content += f"\nCURRENT_PROJECT={project_id}\n"
        env_path.write_text(content)
    return f"Switched to {project_id}"

def tool_read(file_path: str):
    p = Path(PROJECTS[CURRENT_PROJECT]) / file_path
    if not p.exists():
        return f"Not found: {p}"
    return p.read_text(encoding='utf-8', errors='ignore')[:8000]

def tool_write(file_path: str, content: str):
    p = Path(PROJECTS[CURRENT_PROJECT]) / file_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8')
    return f"Wrote {len(content)} chars to {p}"

def tool_shell(command: str):
    lowered = command.lower()
    for bad in SHELL_DENYLIST:
        if bad in lowered:
            logger.warning("Blocked denylisted command: %s", bad)
            return f"Blocked: command matches denylisted pattern {bad!r}"
    try:
        root = PROJECTS[CURRENT_PROJECT]
        if sys.platform == "win32":
            r = subprocess.run(command, shell=True, cwd=root, capture_output=True, text=True, timeout=120)
        else:
            args = shlex.split(command)
            r = subprocess.run(args, shell=False, cwd=root, capture_output=True, text=True, timeout=120)
        return f"Exit {r.returncode}:\n{r.stdout[-5000:]}\n{r.stderr[-2000:]}"
    except subprocess.TimeoutExpired:
        logger.error("Command timed out after 120s: %s", command)
        return "Error: command timed out after 120s"
    except Exception as e:
        logger.exception("Shell command failed: %s", command)
        return f"Error: {e}"

def tool_run_tests(test_command: str = None):
    proj_root = Path(PROJECTS[CURRENT_PROJECT])
    if not test_command:
        if (proj_root / "package.json").exists():
            test_command = "npm test"
        elif (proj_root / "pytest.ini").exists() or (proj_root / "pyproject.toml").exists():
            test_command = "python -m pytest"
        elif (proj_root / "Makefile").exists():
            test_command = "make test"
        else:
            test_command = "python -m pytest"
    return tool_shell(test_command)

def tool_lint(lint_command: str = None):
    proj_root = Path(PROJECTS[CURRENT_PROJECT])
    if not lint_command:
        if (proj_root / "package.json").exists():
            lint_command = "npm run lint"
        elif (proj_root / "pyproject.toml").exists() or (proj_root / "ruff.toml").exists():
            lint_command = "ruff check ."
        else:
            lint_command = "ruff check ."
    return tool_shell(lint_command)

def tool_typecheck(typecheck_command: str = None):
    proj_root = Path(PROJECTS[CURRENT_PROJECT])
    if not typecheck_command:
        if (proj_root / "tsconfig.json").exists():
            typecheck_command = "npx tsc --noEmit"
        else:
            typecheck_command = "mypy ."
    return tool_shell(typecheck_command)

def tool_git_commit(message: str = None, add_all: bool = True):
    if add_all:
        result = tool_shell("git add -A")
        if "Error" in result or "fatal" in result:
            return f"Git add failed: {result}"

    if not message:
        diff_result = tool_shell("git diff --cached --name-only")
        if "Error" in diff_result or not diff_result.strip():
            return "No staged changes to commit"

        files = diff_result.strip().split('\n')
        commit_type = "feat"
        if any(f.startswith("test") or "test" in f for f in files):
            commit_type = "test"
        elif any(f.endswith(".md") for f in files):
            commit_type = "docs"
        elif any("fix" in f.lower() or "bug" in f.lower() for f in files):
            commit_type = "fix"
        elif any(f.endswith((".json", ".toml", ".yaml", ".yml", ".ini")) for f in files):
            commit_type = "chore"

        message = f"{commit_type}: auto-commit from agent task ({len(files)} files)"

    return tool_shell(f'git commit -m "{shlex.quote(message)}"')

def tool_git_status():
    return tool_shell("git status --short")

TOOLS = [
    {"type": "function", "function": {"name": "search_brain", "description": "Search all repos", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read file", "parameters": {"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Write file", "parameters": {"type": "object", "properties": {"file_path": {"type": "string"}, "content": {"type": "string"}}, "required": ["file_path", "content"]}}},
    {"type": "function", "function": {"name": "run_shell", "description": "Run shell command", "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}},
    {"type": "function", "function": {"name": "run_tests", "description": "Run tests", "parameters": {"type": "object", "properties": {"test_command": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {"name": "lint", "description": "Run linter", "parameters": {"type": "object", "properties": {"lint_command": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {"name": "typecheck", "description": "Run type checker", "parameters": {"type": "object", "properties": {"typecheck_command": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {"name": "git_commit", "description": "Commit changes", "parameters": {"type": "object", "properties": {"message": {"type": "string"}, "add_all": {"type": "boolean"}}, "required": []}}},
    {"type": "function", "function": {"name": "git_status", "description": "Get git status", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "self_heal", "description": "Run a test command and auto-fix code", "parameters": {"type": "object", "properties": {"target_file": {"type": "string"}, "test_command": {"type": "string"}}, "required": ["target_file", "test_command"]}}},
    {"type": "function", "function": {"name": "list_projects", "description": "List projects", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "switch_project", "description": "Switch project", "parameters": {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]}}},
    {"type": "function", "function": {"name": "gemini_query", "description": "Query Gemini", "parameters": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}}},
]

TOOL_MAP = {
    "search_brain": lambda query: search_brain(query),
    "read_file": tool_read,
    "write_file": tool_write,
    "run_shell": tool_shell,
    "run_tests": tool_run_tests,
    "lint": tool_lint,
    "typecheck": tool_typecheck,
    "git_commit": tool_git_commit,
    "git_status": tool_git_status,
    "self_heal": lambda target_file, test_command: SelfHealingRunner(agent_executor=None, max_retries=3).run_with_self_healing(target_file, test_command),
    "list_projects": tool_list_projects,
    "switch_project": tool_switch_project,
    "gemini_query": tool_gemini_query,
}

class SelfHealingRunner:
    def __init__(self, agent_executor, max_retries: int = 3):
        self.agent = agent_executor
        self.max_retries = max_retries

    async def run_with_self_healing(self, target_file: str, test_command: str) -> Dict[str, Any]:
        for attempt in range(1, self.max_retries + 1):
            logger.info(f"🔄 Execution Attempt {attempt}/{self.max_retries} for {target_file}")
            test_output = tool_shell(test_command)

            if "Exit 0" in test_output or "All checks passed" in test_output:
                logger.info(f" Execution succeeded on attempt {attempt}")
                return {"status": "success", "attempts": attempt, "output": test_output}

            logger.warning(f"❌ Failure detected on attempt {attempt}. Triggering reflection...")
            file_content = tool_read(target_file)

            reflection_prompt = f"""
            The execution of command '{test_command}' failed with the following output:
            {test_output}
            Here is the current content of '{target_file}':
            {file_content}
            Analyze the error and generate the corrected version of '{target_file}'.
            Return ONLY the updated python file content without markdown code blocks.
            """

            fixed_code = await self._get_fix_from_llm(reflection_prompt)
            tool_write(target_file, fixed_code)

        return {
            "status": "failed",
            "attempts": self.max_retries,
            "last_output": test_output
        }

    async def _get_fix_from_llm(self, prompt: str) -> str:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": EDITOR_MODEL,
                "messages": [
                    {"role": "system", "content": "You are an expert code fixer. Return only the corrected file content without any markdown or explanation."},
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }
            async with session.post(OLLAMA_CHAT_URL, json=payload, timeout=aiohttp.ClientTimeout(total=300)) as resp:
                data = await resp.json()
                return data["message"]["content"].strip()

def _projects_line():
    return f"Projects: {list(PROJECTS.keys())}, Current: {CURRENT_PROJECT} at {PROJECTS.get(CURRENT_PROJECT)}"

ARCHITECT_SYSTEM = f"""You are Architect Agent - senior system designer.
{_projects_line()}
You plan solutions, search brain for patterns, break tasks into steps.
ALWAYS search_brain first. Output a clear plan with files to create/edit.
"""

EDITOR_SYSTEM = f"""You are Editor Agent - expert coder.
You implement plans from Architect. You write clean, tested code.
{_projects_line()}
Use tools to read/write files, run shell. Small diffs, conventional commits.
"""

TESTER_SYSTEM = """You are Tester Agent - QA engineer.
You MUST run actual tests and lint commands to verify changes work.
NEVER fabricate test results - you MUST invoke run_shell to execute real test commands.
"""

# Tools whose invocation counts as a real verification step for the auto-commit gate.
_TEST_TOOLS = {"run_shell", "run_tests", "lint", "typecheck"}
# Command fragments indicating a test/lint/typecheck/build run (case-insensitive).
_TEST_CMD_HINTS = (" test", "pytest", " npm test", "npm run lint", "npm run build",
                   " tsc", "mypy", "ruff", "vitest", "jest", "make test")

def _tester_ran_pass(tester: Agent) -> bool:
    """True only if the Tester actually invoked a test/lint tool that passed clean.

    Unlike a substring check on the Tester's prose (which the model can fabricate),
    this inspects the recorded tool invocations in history and requires:
      1. a tool message whose tool name is a test/lint/typecheck tool, and
      2. for run_shell, the command actually looks like a test/lint/build/ci run, and
      3. that tool's recorded result shows a clean exit (Exit 0:).
    """
    for m in tester.history:
        if m.get("role") != "tool":
            continue
        name = m.get("name")
        if name not in _TEST_TOOLS:
            continue
        args = m.get("args") or {}
        cmd = str(args.get("command") or args.get("test_command") or args.get("lint_command") or args.get("typecheck_command") or "")
        if name == "run_shell" and not any(h in cmd.lower() for h in _TEST_CMD_HINTS):
            continue
        content = m.get("content") or ""
        if "Exit 0:" in content:
            return True
    return False

async def run_multi_agent(task: str):
    logger.info("Multi-Agent Task: %s", task)
    session_id = uuid.uuid4().hex

    logger.info("[Researcher] Searching brain...")
    brain_results = await search_brain(task, top_k=8)
    brain_context = "\n".join(f"[{r['project_id']}/{r['file_path']}] {r['content'][:800]}" for r in brain_results)
    try:
        await save_conversation(session_id, "tool", brain_context[:8000], project_id=CURRENT_PROJECT)
    except Exception as e:
        logger.warning("Brain context save failed: %s", e)

    architect = Agent("Architect", ARCHITECT_MODEL, ARCHITECT_SYSTEM)
    plan = await architect.chat(
        f"Task: {task}\n\nRelevant code from brain:\n{brain_context}\n\nCreate a plan.",
        tools=TOOLS, tool_map=TOOL_MAP
    )
    await persist_agent_history(session_id, [architect])

    editor = Agent("Editor", EDITOR_MODEL, EDITOR_SYSTEM)
    implementation = await editor.chat(
        f"Task: {task}\n\nArchitect plan:\n{plan}\n\nImplement it.",
        tools=TOOLS, tool_map=TOOL_MAP
    )
    await persist_agent_history(session_id, [editor])

    tester = Agent("Tester", EDITOR_MODEL, TESTER_SYSTEM)
    test_result = await tester.chat(
        f"Task was: {task}\nPlan: {plan}\nTest and verify.",
        tools=TOOLS, tool_map=TOOL_MAP
    )
    await persist_agent_history(session_id, [tester])

    # Success-gated auto-commit: only commit if the Tester actually ran a test/lint
    # tool that passed cleanly (observed invocation, not fabricated prose).
    if AUTO_COMMIT and _tester_ran_pass(tester):
        status_result = tool_git_status()
        if status_result.strip():
            tool_git_commit(f"feat(agent): {task[:72]}")

    if memory_mgr:
        try:
            await _get_pool()  # Ensure pool is initialized for memory_mgr
            lesson_txt = f"Task: {task}\nPlan: {plan[:500]}\nResult: {test_result[:500]}"
            lesson_emb = await embed(lesson_txt[:500])
            await memory_mgr.add_memory("lesson", lesson_txt, CURRENT_PROJECT, embedding=lesson_emb)
        except Exception as e:
            logger.warning("Memory failed: %s", e)

    logger.info("Multi-agent task complete: %s", task)

async def run_multi_agent_stream(task: str) -> AsyncGenerator[Dict[str, Any], None]:
    """Stream multi-agent progress as events for SSE (Completed Implementation)"""
    session_id = uuid.uuid4().hex
    yield {"type": "start", "session_id": session_id, "task": task}

    # 1. Researcher Phase
    yield {"type": "phase", "phase": "researcher", "status": "started", "message": "Searching brain..."}
    brain_results = await search_brain(task, top_k=8)
    brain_context = "\n".join(f"[{r['project_id']}/{r['file_path']}] {r['content'][:800]}" for r in brain_results)
    yield {"type": "phase", "phase": "researcher", "status": "completed", "message": f"Found {len(brain_results)} relevant chunks", "data": {"chunks": len(brain_results)}}
    
    try:
        await save_conversation(session_id, "tool", brain_context[:8000], project_id=CURRENT_PROJECT)
    except Exception as e:
        yield {"type": "warning", "message": f"Brain context save failed: {e}"}

    # 2. Architect Phase
    yield {"type": "phase", "phase": "architect", "status": "started", "message": "Planning solution..."}
    architect = Agent("Architect", ARCHITECT_MODEL, ARCHITECT_SYSTEM)
    plan = await architect.chat(
        f"Task: {task}\n\nRelevant code from brain:\n{brain_context}\n\nCreate a plan: which project, which files, what changes, in what order. Be specific.",
        tools=TOOLS, tool_map=TOOL_MAP
    )
    yield {"type": "phase", "phase": "architect", "status": "completed", "message": "Plan created", "data": {"plan": plan[:2000]}}
    try:
        await persist_agent_history(session_id, [architect])
    except Exception as e:
        yield {"type": "warning", "message": f"Architect save failed: {e}"}

    # 3. Editor Phase
    yield {"type": "phase", "phase": "editor", "status": "started", "message": "Implementing..."}
    editor = Agent("Editor", EDITOR_MODEL, EDITOR_SYSTEM)
    implementation = await editor.chat(
        f"Task: {task}\n\nArchitect plan:\n{plan}\n\nRelevant code:\n{brain_context}\n\nImplement it. Use tools to create/edit files.",
        tools=TOOLS, tool_map=TOOL_MAP
    )
    yield {"type": "phase", "phase": "editor", "status": "completed", "message": "Implementation done", "data": {"implementation": implementation[:2000]}}
    try:
        await persist_agent_history(session_id, [editor])
    except Exception as e:
        yield {"type": "warning", "message": f"Editor save failed: {e}"}

    # 4. Tester Phase
    yield {"type": "phase", "phase": "tester", "status": "started", "message": "Running tests..."}
    tester = Agent("Tester", EDITOR_MODEL, TESTER_SYSTEM)
    test_result = await tester.chat(
        f"Task was: {task}\nPlan: {plan}\nImplementation done. Now test it - run relevant tests, lint, check if it works. Fix if needed.",
        tools=TOOLS, tool_map=TOOL_MAP
    )
    yield {"type": "phase", "phase": "tester", "status": "completed", "message": "Tests completed", "data": {"test_result": test_result[:2000]}}
    try:
        await persist_agent_history(session_id, [tester])
    except Exception as e:
        yield {"type": "warning", "message": f"Tester save failed: {e}"}

    # 5. Memory Phase & Final Stream Completion
    if memory_mgr:
        try:
            await _get_pool()  # Ensure pool is initialized for memory_mgr
            lesson_txt = f"Task: {task}\nPlan: {plan[:500]}\nResult: {test_result[:500]}"
            lesson_emb = await embed(lesson_txt[:500])
            await memory_mgr.add_memory("lesson", lesson_txt, CURRENT_PROJECT, embedding=lesson_emb)
            yield {"type": "phase", "phase": "memory", "status": "completed", "message": "Lesson recorded in long-term memory"}
        except Exception as e:
            yield {"type": "warning", "message": f"Memory save failed: {e}"}

    # Success-gated auto-commit (streaming): commit only if the Tester actually ran a
    # test/lint tool that passed cleanly (observed invocation, not fabricated prose).
    if AUTO_COMMIT and _tester_ran_pass(tester):
        status_result = tool_git_status()
        if status_result.strip():
            tool_git_commit(f"feat(agent): {task[:72]}")
            yield {"type": "phase", "phase": "commit", "status": "completed", "message": "Auto-committed changes (tests passed)"}

    yield {"type": "done", "session_id": session_id, "message": "All agent phases completed successfully"}

def serve_fastapi():
    """Run the FastAPI server for Code It dashboard integration"""
    import uvicorn
    from api import app as fastapi_app
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--serve":
            serve_fastapi()
        else:
            task_input = " ".join(sys.argv[1:])
            asyncio.run(run_multi_agent(task_input))
    else:
        print("Usage: python brain_agent_v4.py <task_description>")
        print("       python brain_agent_v4.py --serve  # Run FastAPI server on port 8000")
