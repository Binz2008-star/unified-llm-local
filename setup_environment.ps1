# setup_environment.ps1 - Environment initialization for Second Brain MCP
# Uses uv for Python isolation and npx for Node.js tools (no global npm installs)

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Second Brain MCP Environment Setup" -ForegroundColor White -BackgroundColor DarkCyan
Write-Host "=" * 60 -ForegroundColor Cyan

# 1. Ensure UV is installed
Write-Host "1. Checking UV installation..." -ForegroundColor Green
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "   Installing UV..." -ForegroundColor Yellow
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
} else {
    Write-Host "   UV already installed" -ForegroundColor Green
}

# 2. Create isolated Python venv using uv if needed
Write-Host "2. Checking Python environment..." -ForegroundColor Green
cd X:\second-brain-kb
if (-not (Test-Path ".venv\pyvenv.cfg")) {
    Write-Host "   Creating fresh Python venv with uv..." -ForegroundColor Yellow
    rm -Force -Recurse .venv 2>$null
    uv venv .venv
}
Write-Host "   Python venv ready" -ForegroundColor Green

# 3. Activate venv and install Python packages
Write-Host "3. Installing Python packages into venv..." -ForegroundColor Green
.\.venv\Scripts\activate.ps1
uv pip install -e . 2>/dev/null
uv pip install mcp asyncpg aiohttp python-dotenv sentence-transformers 2>&1 | Write-Host "   " -ForegroundColor Cyan
Write-Host "   Packages installed" -ForegroundColor Green

# 4. Verify MCP server can start
Write-Host "4. Verifying MCP server..." -ForegroundColor Green
python -c "
import sys
sys.path.insert(0, r'X:\second-brain-kb')
from mcp_server_v4 import server
print('   MCP Server v4: OK - tools=' + str(len(server.tools)) if 'server' in dir() else 'Import OK')
" 2>&1 | Write-Host "   " -ForegroundColor Cyan
Write-Host "   MCP Server verification complete" -ForegroundColor Green

# 5. Validate Mcp-All.json configuration
Write-Host "5. Validating Mcp-All.json..." -ForegroundColor Green
if (Test-Path "Mcp-All.json") {
    Write-Host "   Mcp-All.json found - checking universal-second-brain path..." -ForegroundColor Cyan
    $json = Get-Content "Mcp-All.json" -Raw | ConvertFrom-Json
    if ($json.mcpServers.'universal-second-brain') {
        $entry = $json.mcpServers.'universal-second-brain'
        Write-Host "   Command: $($entry.command)" -ForegroundColor Green
        Write-Host "   Args: $($entry.args -join ' ')" -ForegroundColor Green
        if ($entry.command -match 'mcp_server_v4') {
            Write-Host "   ✓ Configuration correct: using mcp_server_v4.py" -ForegroundColor Green
        } else {
            Write-Host "   ✗ Configuration issue: should use mcp_server_v4.py" -ForegroundColor Red
        }
    } else {
        Write-Host "   ✗ universal-second-brain entry not found in Mcp-All.json" -ForegroundColor Red
    }
} else {
    Write-Host "   ⚠ Mcp-All.json not found at root" -ForegroundColor Yellow
}

Write-Host "" -ForegroundColor Cyan
Write-Host "Setup Complete! Ready for MCP client integration." -ForegroundColor White -BackgroundColor DarkCyan