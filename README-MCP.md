
# 🧠 Second Brain - ALL MCPs for Real Coding

You now have 11 MCPs that let you work on ANY project + create new projects.

## MCP Server Configuration

Your MCP setup uses two configuration files:

1. **`Mcp-All.json`** (`X:\second-brain-kb\Mcp-All.json`): Defines 11 MCP servers including the custom `universal-second-brain` server that wraps the Second Brain v4 brain agent.
2. **`opencode.json`** (`C:\Users\loyal\.config\opencode\opencode.json`): Registered as `second-brain-v4` - runs `mcp_server_v4.py` with an isolated Python venv.

## Custom Server: `universal-second-brain`

The `universal-second-brain` MCP server (configured in `Mcp-All.json`) provides these tools via the stdio-based `mcp_server_v4.py`:

- **search_brain** - Hybrid semantic search across all indexed projects (vector + BM25)
- **agent_task** - Run the multi-agent pipeline (Researcher→Architect→Editor→Tester→Memory)
- **get_status** - KB + DB health / counts (chunks_v4, memory, code_graph, projects)
- **list_memory** - Read long-term memories from Neon DB
- **apply_patch** - Apply unified diff patches to files
- **replace_block** - Replace code blocks in files

The server is configured to use `.venv` Python isolation and connects to Neon PostgreSQL + local Ollama.

## Full Stack (11 MCPs)

1. filesystem - access X:/, C:/Users/loyal, C:/projects - ANY project
2. git - git ops
3. github - create repos, PRs
4. brave-search - search docs
5. fetch - fetch templates
6. postgres - query Neon brain directly
7. puppeteer - browser test new projects
8. memory - long-term memory
9. sequential-thinking - planning
10. time - time
11. universal-second-brain - Second Brain v4 MCP (vector search + agent pipeline)

## Install

```powershell
cd X:\second-brain-kb
powershell -ExecutionPolicy Bypass -File install_all_mcps.ps1
setx GITHUB_TOKEN ghp_...
setx BRAVE_API_KEY ...
setx NEON_DSN ...
```

Copy opencode_final.json to:
- OpenCode: %USERPROFILE%\.config\opencode\opencode.json
- Claude: %APPDATA%\Claude\claude_desktop_config.json
- Cursor: %APPDATA%\Cursor\mcp.json

## Create ANY new project

In OpenCode/Claude:
```
> create_project type=nextjs name=my-saas path=X:/projects
> create_project type=fastapi name=my-api path=X:/projects
> create_project type=fullstack name=my-startup path=X:/

> analyze_project path=X:/some-cloned-repo
> search_second_brain query="how to do auth"
> shell_run command="npm install" cwd="X:/projects/my-saas"
> shell_run command="npm run dev" cwd="X:/projects/my-saas"
```

## Dynamic indexing for ANY project

To add any new project to second-brain:

```powershell
python ingest.py --project-path X:/projects/my-new-app --project-id my-new-app
# Then search it:
python query.py "auth logic in my-new-app"
```

## Real coding workflow

1. User: "Create SaaS with auth from content-engine"
2. Agent:
   - search_second_brain "auth middleware"
   - create_project fullstack saas X:/
   - file_read X:/content engine/.../auth.py
   - file_write X:/saas/backend/auth.py (adapted)
   - shell_run "docker compose up"
   - git_status + git_commit
3. Done - new project built using old patterns

This works for ANY given project, not just your 3.
