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
        types.Tool(name="bug_create",
                   description="Create a new bug report with details.",
                   inputSchema={"type": "object", "properties": {
                       "project_id": {"type": "string", "description": "Project ID (content-engine, rico, lvyy, second-brain)"},
                       "title": {"type": "string", "description": "Bug title"},
                       "description": {"type": "string", "description": "Detailed description"},
                       "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"], "default": "medium"},
                       "bug_type": {"type": "string", "enum": ["logic", "performance", "security", "ui", "test", "dependency", "other"]},
                       "file_path": {"type": "string", "description": "Affected file path"},
                       "line_start": {"type": "integer"},
                       "line_end": {"type": "integer"},
                       "tags": {"type": "array", "items": {"type": "string"}},
                   }, "required": ["project_id", "title", "description"]}),
        types.Tool(name="bug_list",
                   description="List bugs with filters.",
                   inputSchema={"type": "object", "properties": {
                       "project_id": {"type": "string"},
                       "status": {"type": "string", "enum": ["open", "investigating", "fixing", "fixed", "verified", "closed"]},
                       "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                       "limit": {"type": "integer", "default": 20},
                   }}),
        types.Tool(name="bug_get",
                   description="Get details of a specific bug.",
                   inputSchema={"type": "object", "properties": {
                       "bug_id": {"type": "integer", "description": "Bug ID"},
                   }, "required": ["bug_id"]}),
        types.Tool(name="bug_update",
                   description="Update bug status or details.",
                   inputSchema={"type": "object", "properties": {
                       "bug_id": {"type": "integer", "description": "Bug ID"},
                       "status": {"type": "string", "enum": ["open", "investigating", "fixing", "fixed", "verified", "closed"]},
                       "assignee": {"type": "string"},
                       "fix_commit_hash": {"type": "string"},
                   }, "required": ["bug_id"]}),
        types.Tool(name="bug_fix",
                   description="Run bug fixer agent to analyze and fix a bug automatically.",
                   inputSchema={"type": "object", "properties": {
                       "bug_id": {"type": "integer", "description": "Bug ID to fix"},
                       "auto_apply": {"type": "boolean", "default": False, "description": "Automatically apply the fix"},
                   }, "required": ["bug_id"]}),
        types.Tool(name="bug_scan",
                   description="Scan code for potential bugs using patterns and static analysis.",
                   inputSchema={"type": "object", "properties": {
                       "project_id": {"type": "string", "description": "Project to scan"},
                       "patterns": {"type": "array", "items": {"type": "string"}, "description": "Custom patterns to search for"},
                   }, "required": ["project_id"]}),
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

    elif name == "bug_create":
        return await _bug_create(args)

    elif name == "bug_list":
        return await _bug_list(args)

    elif name == "bug_get":
        return await _bug_get(args)

    elif name == "bug_update":
        return await _bug_update(args)

    elif name == "bug_fix":
        return await _bug_fix(args)

    elif name == "bug_scan":
        return await _bug_scan(args)

    return types.CallToolResult(isError=True, content=_text(f"Unknown tool: {name}"))


async def _bug_create(args: Dict[str, Any]) -> types.CallToolResult:
    import asyncpg
    pool = await ba._get_pool()
    async with pool.acquire() as conn:
        bug_id = await conn.fetchval("""
            INSERT INTO bugs (project_id, title, description, severity, bug_type, file_path, line_start, line_end, tags)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
        """, args.get("project_id"), args.get("title"), args.get("description"),
            args.get("severity", "medium"), args.get("bug_type", "other"),
            args.get("file_path"), args.get("line_start"), args.get("line_end"),
            args.get("tags", []))
    return types.CallToolResult(content=_text(f"Bug created with ID: {bug_id}"))


async def _bug_list(args: Dict[str, Any]) -> types.CallToolResult:
    import asyncpg
    pool = await ba._get_pool()
    conditions = []
    params = []
    param_idx = 1
    
    if args.get("project_id"):
        conditions.append(f"project_id = ${param_idx}")
        params.append(args["project_id"])
        param_idx += 1
    if args.get("status"):
        conditions.append(f"status = ${param_idx}")
        params.append(args["status"])
        param_idx += 1
    if args.get("severity"):
        conditions.append(f"severity = ${param_idx}")
        params.append(args["severity"])
        param_idx += 1
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    limit = args.get("limit", 20)
    
    async with pool.acquire() as conn:
        rows = await conn.fetch(f"""
            SELECT id, project_id, title, severity, status, bug_type, file_path, 
                   assignee, created_at, updated_at
            FROM bugs {where_clause}
            ORDER BY created_at DESC LIMIT ${param_idx}
        """, *params, limit)
    return types.CallToolResult(content=_text(json.dumps([dict(r) for r in rows], indent=2, default=str)))


async def _bug_get(args: Dict[str, Any]) -> types.CallToolResult:
    import asyncpg
    pool = await ba._get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM bugs WHERE id = $1", args.get("bug_id"))
    if not row:
        return types.CallToolResult(isError=True, content=_text(f"Bug {args.get('bug_id')} not found"))
    return types.CallToolResult(content=_text(json.dumps(dict(row), indent=2, default=str)))


async def _bug_update(args: Dict[str, Any]) -> types.CallToolResult:
    import asyncpg
    pool = await ba._get_pool()
    bug_id = args.get("bug_id")
    updates = []
    params = [bug_id]
    param_idx = 2
    
    if args.get("status"):
        updates.append(f"status = ${param_idx}")
        params.append(args["status"])
        param_idx += 1
    if args.get("assignee"):
        updates.append(f"assignee = ${param_idx}")
        params.append(args["assignee"])
        param_idx += 1
    if args.get("fix_commit_hash"):
        updates.append(f"fix_commit_hash = ${param_idx}")
        params.append(args["fix_commit_hash"])
        param_idx += 1
    
    updates.append("updated_at = NOW()")
    if "fixed" in (args.get("status") or ""):
        updates.append("fixed_at = NOW()")
    
    if not updates:
        return types.CallToolResult(isError=True, content=_text("No updates provided"))
    
    async with pool.acquire() as conn:
        await conn.execute(f"UPDATE bugs SET {', '.join(updates)} WHERE id = $1", *params)
    return types.CallToolResult(content=_text(f"Bug {bug_id} updated"))


async def _bug_fix(args: Dict[str, Any]) -> types.CallToolResult:
    bug_id = args.get("bug_id")
    auto_apply = args.get("auto_apply", False)
    
    # Get bug details
    import asyncpg
    pool = await ba._get_pool()
    async with pool.acquire() as conn:
        bug = await conn.fetchrow("SELECT * FROM bugs WHERE id = $1", bug_id)
    
    if not bug:
        return types.CallToolResult(isError=True, content=_text(f"Bug {bug_id} not found"))
    
    # Build fix task
    task = f"""Fix the following bug:

BUG #{bug_id}: {bug['title']}
Project: {bug['project_id']}
File: {bug['file_path'] or 'Unknown'}
Type: {bug['bug_type']}
Severity: {bug['severity']}

Description:
{bug['description']}

Please analyze the code, identify the root cause, and provide a fix.
"""
    
    if auto_apply:
        task += "\nApply the fix directly to the codebase."
    else:
        task += "\nProvide the fix as a patch/diff for review."
    
    # Run multi-agent to fix
    try:
        await ba.run_multi_agent(task)
        # Update bug status
        async with pool.acquire() as conn:
            await conn.execute("UPDATE bugs SET status = 'fixing', updated_at = NOW() WHERE id = $1", bug_id)
        return types.CallToolResult(content=_text(f"Bug fixer agent completed for bug {bug_id}. Check results and update status."))
    except Exception as e:
        return types.CallToolResult(isError=True, content=_text(f"Bug fixer failed: {e}"))


async def _bug_scan(args: Dict[str, Any]) -> types.CallToolResult:
    project_id = args.get("project_id")
    patterns = args.get("patterns", [])
    
    # Default bug patterns
    default_patterns = [
        "TODO.*FIXME",
        "XXX.*HACK",
        "except: pass",
        "except Exception: pass",
        "print\\(.*password",
        "eval\\(",
        "exec\\(",
        "shell=True",
        "verify=False",
        "TODO.*security",
        "FIXME.*bug",
    ]
    all_patterns = list(set(default_patterns + patterns))
    
    # Search for patterns in code
    import asyncpg
    pool = await ba._get_pool()
    results = []
    
    for pattern in all_patterns:
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT file_path, chunk_name, content, chunk_index
                FROM chunks_v4
                WHERE project_id = $1 AND content ~* $2
                LIMIT 10
            """, project_id, pattern)
        
        for row in rows:
            results.append({
                "pattern": pattern,
                "file": row["file_path"],
                "function": row["chunk_name"],
                "line": row["chunk_index"],
                "snippet": row["content"][:200]
            })
    
    # Create bug reports for findings
    bugs_created = 0
    for result in results[:20]:  # Limit to 20 findings
        bug_title = f"Potential issue: {result['pattern']} in {result['file']}"
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO bugs (project_id, title, description, severity, bug_type, file_path, tags)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, project_id, bug_title, 
                f"Pattern '{result['pattern']}' found in {result['function']}:\n{result['snippet']}",
                "low", "logic", result["file"], [result["pattern"], "auto-scan"])
            bugs_created += 1
    
    return types.CallToolResult(content=_text(f"Scanned {project_id}: found {len(results)} matches, created {bugs_created} bug reports"))


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