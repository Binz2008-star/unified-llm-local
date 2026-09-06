# Fix heimdall MCP error -32000: Connection closed

## Cause
OpenCode tried to start `heimdall mcp` but process closed immediately.
Common reasons:
1. Node < 22.5 (heimdall journal uses node:sqlite, needs >=22.5)
2. heimdall not installed globally
3. graft backend not built
4. heimdall config missing

## Fix steps in PowerShell:

# 1. Check Node version (must be >=22.5)
node --version
# If <22.5, update Node.js from nodejs.org

# 2. Install heimdall globally
npm i -g @arihantdeva/heimdall
heimdall --version

# 3. Init heimdall (creates ~/.heimdall/config)
heimdall init --harness opencode
heimdall init --detect

# 4. Test MCP server manually (should stay running, not exit)
heimdall mcp
# If it exits immediately, check error - likely Node version or missing ~/.heimdall

# 5. Check doctor (needs graft backend, but MCP should work without it for insert/search)
heimdall doctor
# If HEALTHY, great. If not, MCP still works for insert but search needs graft

# 6. In OpenCode, disable failing heimdall-npx if global works
# Edit opencode.json and remove heimdall-npx if heimdall works

# 7. Restart OpenCode
# OpenCode should show:
# MCP
# • heimdall Connected
# • universal-second-brain Connected

## If still Connection closed:

Try direct npx version:
In opencode.json, use:
"heimdall": {
  "command": "npx",
  "args": ["-y", "@arihantdeva/heimdall", "mcp"]
}

## LSPs disabled - that's normal on Windows, not related to MCP
Enable in opencode settings if needed, but not required for second-brain.
