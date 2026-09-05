# Second Brain - Ultimate Setup with Agent + MCPs

## One Terminal Agent (brain-agent.py)

This is your OpenCode replacement - ONE terminal that:
- Searches across all repos (semantic)
- Switches projects
- Creates/deletes files
- Runs shell commands (npm, pip, pytest, git)
- Full autonomous agent

### Setup

```powershell
cd X:\second-brain-kb
pip install asyncpg aiohttp python-dotenv sentence-transformers torch --extra-index-url https://download.pytorch.org/whl/cpu
pip install mcp  # for MCP server

# Make sure Ollama models exist
ollama list
# Need: nomic-embed-text, qwen2.5-coder:14b-16k, deepseek-r1:14b-16k

# If not, create 16k models
"FROM qwen2.5-coder:14b`nPARAMETER num_ctx 16384" | Set-Content Modelfile-16k
ollama create qwen2.5-coder:14b-16k -f Modelfile-16k
"FROM deepseek-r1:14b`nPARAMETER num_ctx 16384" | Set-Content Modelfile-r1-16k
ollama create deepseek-r1:14b-16k -f Modelfile-r1-16k
```

### Use Agent

```powershell
# Interactive (like opencode)
python brain-agent.py

# One-shot tasks
python brain-agent.py "add JWT auth from content-engine to lvyy"
python brain-agent.py "create src/utils/helpers.py with common functions"
python brain-agent.py "run tests in content-engine and fix failures"
python brain-agent.py "delete all tmp files in lvyy"
```

### Agent Tools

The agent has these tools built-in (Ollama tool calling):
- `search_brain(query)` - semantic search across all repos
- `list_projects()` / `switch_project(id)` - switch repos
- `list_files(path)`, `read_file(path)`, `write_file(path, content)`, `delete_file(path)`
- `run_shell(command)` - npm install, pytest, git, etc
- `git_status()`

It auto-switches projects when you mention them.

### Example Session

```
[lvyy] You: add auth from content-engine to lvyy

🔧 Using 3 tools...
  → search_brain({"query": "auth JWT middleware content-engine"})
    ↳ [content-engine/src/api.py] JWT verification...
  → read_file({"file_path": "src/auth/middleware.py"})
    ↳ file content...
  → write_file({"file_path": "src/auth/jwt.py", "content": "..."})
    ↳ ✅ Wrote 342 chars...

🧠 [lvyy]: Added JWT auth similar to content-engine. Created src/auth/jwt.py
Need to install PyJWT: run_shell("pip install PyJWT")
```

## MCPs - Required + Recommended

### 1. Second Brain MCP (your custom)

File: `X:\second-brain-kb\mcp_server.py`

For OpenCode - add to `opencode.json` in your home:

```json
{
  "mcpServers": {
    "second-brain": {
      "command": "python",
      "args": ["X:/second-brain-kb/mcp_server.py"],
      "env": {
        "NEON_DSN": "your-dsn",
        "OLLAMA_EMBED_URL": "http://127.0.0.1:11434/api/embed"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "C:/Users/loyal/lvyy-ai-sales-agent", "X:/content engine/Robin-Content-Engine-v2"]
    },
    "git": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-git", "--repository", "C:/Users/loyal/lvyy-ai-sales-agent"]
    },
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": {"BRAVE_API_KEY": "your-key"}
    }
  }
}
```

Then in OpenCode you can:
```
> /mcp second-brain search_second_brain "auth pattern"
```

### 2. Essential MCPs to add

Install globally:
```powershell
npm install -g @modelcontextprotocol/server-filesystem
npm install -g @modelcontextprotocol/server-git
npm install -g @modelcontextprotocol/server-brave-search
npm install -g @modelcontextprotocol/server-puppeteer
```

| MCP | What it does | Why you need |
|-----|--------------|--------------|
| filesystem | Read/write files anywhere | Agent needs to edit repos |
| git | Git operations | Commit, diff, branch |
| second-brain (custom) | Semantic search across repos | Your cross-repo memory |
| brave-search | Web search | Find docs, solutions |
| puppeteer | Browser automation | Test web apps |
| postgres | Query Neon directly | Check second-brain DB |

### 3. For Claude Code / Cursor

Claude Code uses same MCP config - add to `~/.claude.json` or `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "second-brain": {
      "command": "python",
      "args": ["X:/second-brain-kb/mcp_server.py"]
    }
  }
}
```

## Docker Auto-Start (One Terminal Forever)

After reboot setup you already did:
- `setx OLLAMA_HOST 0.0.0.0:11434` -> Ollama service listens on 0.0.0.0
- Docker compose `restart: unless-stopped` -> auto starts
- Now you only need: `python brain-agent.py`

To make brain-agent auto-start on boot:
```powershell
# Create shortcut in shell:startup
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\SecondBrainAgent.lnk")
$Shortcut.TargetPath = "C:\Windows\System32\cmd.exe"
$Shortcut.Arguments = "/c cd /d X:\second-brain-kb && python brain-agent.py"
$Shortcut.Save()
```

## Files Overview

- `ingest.py` - Docker indexer (runs 24/7, auto-indexes)
- `brain.py` - Simple Q&A chat
- `brain-agent.py` - FULL AGENT (switch repos, create/delete, shell, tools) - USE THIS
- `mcp_server.py` - MCP server for OpenCode/Claude
- `brain.bat` - Double-click launcher

## Which to use?

- Want simple Q&A? -> `python brain.py`
- Want full OpenCode-like agent that does everything? -> `python brain-agent.py` (RECOMMENDED)
- Want OpenCode to have second-brain memory? -> Add MCP server to opencode.json

All share same Neon + Ollama backend.
