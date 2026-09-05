"""
MCP Server v4 - Second Brain for MCP clients (OpenCode, Desktop, Claude, etc.)
Tools:
  search_brain - hybrid semantic search across all indexed projects
  agent_task   - run the multi-agent pipeline on a task
  get_status   - KB + DB health / counts
  list_memory  - read long-term memory (MB stored in Neon)
Runs over stdio. Register in opencode.json as:
  "mcpServers": { "second-brain": { "command": "python",
                                     "args": ["X:/second-brain-kb/mcp_server_v4.py"] } }
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

from mcp import types
from mcp.server.lowlevel import Server

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

# Make brain_agent_v4 + memory importable from this script's location
for p in [str(ROOT), str(ROOT / "v4-extract" / "second-brain-v4")]:
    if p not in sys.path:
        sys.path.insert(0, p)

import brain_agent_v4 as ba
from memory import MemoryManager

NEON_DSN = os.getenv("NEON_DSN")
memory_mgr = None
try:
    memory_mgr = MemoryManager(None, memory_dir=str(ROOT / "memory"))
except Exception as e:
    print(f"[memory disabled] {e}", file=sys.stderr)


def _text(content: str):
    return [types.TextContent(type="text", text=content)]


async def _handle_list_tools(ctx, params) -> types.ListToolsResult:
    return types.ListToolsResult(tools=[
        types.Tool(name="search_brain",
                   description="Hybrid semantic search across all indexed projects (vector + BM25). Returns ranked code chunks.",
                   inputSchema={"type": "object", "properties": {
                       "query": {"type": "string", "description": "Search query"},
                       "top_k": {"type": "integer", "default": 8, "description": "Number of results"},
                   }, "required": ["query"]}),
        types.Tool(name="agent_task",
                   description="Run the multi-agent pipeline (Researcher->Architect->Editor->Tester->Memory) on a task. Can create/edit files.",
                   inputSchema={"type": "object", "properties": {
                       "task": {"type": "string", "description": "Task description"},
                   }, "required": ["task"]}),
        types.Tool(name="get_status",
                   description="Health check: DB row counts, projects, memory count, configured models.",
                   inputSchema={"type": "object", "properties": {}}),
        types.Tool(name="list_memory",
                   description="List stored long-term memories (facts, preferences, lessons, patterns) from Neon.",
                   inputSchema={"type": "object", "properties": {
                       "limit": {"type": "integer", "default": 50, "description": "Max memories to return"},
                   }}),
        types.Tool(name="apply_patch",
                   description="Apply a unified diff patch to a file in the current project.",
                   inputSchema={"type": "object", "properties": {
                       "target_file": {"type": "string", "description": "Path to the file to patch"},
                       "patch_content": {"type": "string", "description": "Unified diff content to apply"},
                   }, "required": ["target_file", "patch_content"]}),
        types.Tool(name="replace_block",
                   description="Replace a specific block of code in a file with new content.",
                   inputSchema={"type": "object", "properties": {
                       "target_file": {"type": "string", "description": "Path to the file to modify"},
                       "search_block": {"type": "string", "description": "Exact text block to search for"},
                       "replace_block": {"type": "string", "description": "New content to replace with"},
                   }, "required": ["target_file", "search_block", "replace_block"]}),
    ])


async def _handle_call_tool(ctx, params) -> types.CallToolResult:
    name = params.name
    args = params.arguments or {}

    if name == "search_brain":
        query = args.get("query", "")
        top_k = args.get("top_k", 8)
        rows = await ba.search_brain(query, top_k=top_k)
        out = [dict(r) for r in rows]
        return types.CallToolResult(content=_text(json.dumps(out, indent=2, default=str)))

    elif name == "agent_task":
        task = args.get("task", "")
        if not task:
            return types.CallToolResult(isError=True,
                                        content=_text("Missing required argument: task"))
        await ba.run_multi_agent(task)
        return types.CallToolResult(content=_text(json.dumps({"status": "completed", "task": task})))

    elif name == "get_status":
        status = await _status_payload()
        return types.CallToolResult(content=_text(json.dumps(status, indent=2, default=str)))

    elif name == "list_memory":
        limit = args.get("limit", 50)
        mems = await _memory_payload(limit)
        return types.CallToolResult(content=_text(json.dumps(mems, indent=2, default=str)))

    elif name == "apply_patch":
        target_file = args.get("target_file", "")
        patch_content = args.get("patch_content", "")
        if not target_file or not patch_content:
            return types.CallToolResult(isError=True, content=_text("Missing required arguments: target_file and patch_content"))
        result = ba.tool_apply_patch(target_file, patch_content)
        return types.CallToolResult(content=_text(result))

    elif name == "replace_block":
        target_file = args.get("target_file", "")
        search_block = args.get("search_block", "")
        replace_block = args.get("replace_block", "")
        if not target_file or not search_block or not replace_block:
            return types.CallToolResult(isError=True, content=_text("Missing required arguments: target_file, search_block, replace_block"))
        result = ba.tool_replace_block(target_file, search_block, replace_block)
        return types.CallToolResult(content=_text(result))

    return types.CallToolResult(isError=True, content=_text(f"Unknown tool: {name}"))


async def _status_payload() -> Dict[str, Any]:
    import asyncpg
    payload = {
        "model": getattr(ba, "ARCHITECT_MODEL", None),
        "embed_model": getattr(ba, "EMBED_MODEL", None),
        "current_project": getattr(ba, "CURRENT_PROJECT", None),
        "projects": {k: str(v) for k, v in ba.PROJECTS.items()},
    }
    try:
        pool = await ba._get_pool()
        async with pool.acquire() as conn:
            payload["chunks_v4"] = await conn.fetchval("SELECT COUNT(*) FROM chunks_v4")
            try:
                payload["memory"] = await conn.fetchval("SELECT COUNT(*) FROM memory")
            except Exception:
                payload["memory"] = 0
            try:
                payload["code_graph"] = await conn.fetchval("SELECT COUNT(*) FROM code_graph")
            except Exception:
                payload["code_graph"] = 0
        payload["db"] = "ok"
    except Exception as e:
        payload["db"] = f"error: {e}"
    return payload


async def _memory_payload(limit: int) -> List[Dict[str, Any]]:
    import asyncpg
    pool = await ba._get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, type, left(content, 500) AS content, project_id, created_at "
            "FROM memory ORDER BY id DESC LIMIT $1", limit)
    return [dict(r) for r in rows]


server = Server("second-brain-v4",
                on_list_tools=_handle_list_tools,
                on_call_tool=_handle_call_tool)


async def main():
    async with __import__("mcp.server.stdio", fromlist=["stdio_server"]).stdio_server() as (r, w):
        await server.run(r, w, server.create_initialization_options())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass