
# Install ALL MCPs for real coding
Write-Host "Installing ALL MCP servers..." -ForegroundColor Green

npm install -g @modelcontextprotocol/server-filesystem
npm install -g @modelcontextprotocol/server-git
npm install -g @modelcontextprotocol/server-github
npm install -g @modelcontextprotocol/server-brave-search
npm install -g @modelcontextprotocol/server-fetch
npm install -g @modelcontextprotocol/server-postgres
npm install -g @modelcontextprotocol/server-puppeteer
npm install -g @modelcontextprotocol/server-memory
npm install -g @modelcontextprotocol/server-sequential-thinking
npm install -g @modelcontextprotocol/server-time

pip install mcp asyncpg aiohttp python-dotenv sentence-transformers

Write-Host "All MCPs installed!" -ForegroundColor Green
Write-Host "Set env vars:" -ForegroundColor Yellow
Write-Host "  setx GITHUB_TOKEN your_github_token"
Write-Host "  setx BRAVE_API_KEY your_brave_key"
Write-Host "  setx NEON_DSN your_neon_dsn"

# Setup Mcp-All.json configuration
Write-Host "Configuring Mcp-All.json..." -ForegroundColor Green
$mcpAllPath = "X:\second-brain-kb\Mcp-All.json"
if (Test-Path $mcpAllPath) {
    $content = Get-Content $mcpAllPath -Raw | ConvertFrom-Json
    # Ensure universal-second-brain is configured
    if (-not $mcpAllPath.mcpServers.'universal-second-brain') {
        $mcpAllPath.mcpServers.'universal-second-brain' = @{
            command = "X:/second-brain-kb/.venv/Scripts/python.exe"
            args    = @("X:/second-brain-kb/mcp_server_v4.py")
            env = @{
                NEON_DSN = $env:NEON_DSN
                OLLAMA_EMBED_URL = "http://127.0.0.1:11434/api/embed"
                EMBED_MODEL = "nomic-embed-text"
            }
            description = "Second Brain v4 MCP - Vector search + Agent pipeline + File ops"
        }
        $mcpAllPath | ConvertTo-Json -Depth 10 | Set-Content $mcpAllPath
        Write-Host "  Mcp-All.json updated" -ForegroundColor Cyan
    } else {
        Write-Host "  Mcp-All.json already configured" -ForegroundColor Yellow
    }
} else {
    Write-Host "  Creating new Mcp-All.json..." -ForegroundColor Cyan
    $newConfig = @{
        mcpServers = @{
            filesystem = @{
                command = "npx"
                args = @("-y", "@modelcontextprotocol/server-filesystem", "X:/", "C:/Users/loyal", "C:/projects")
            }
            git = @{
                command = "npx"
                args = @("-y", "@modelcontextprotocol/server-git")
            }
            github = @{
                command = "npx"
                args = @("-y", "@modelcontextprotocol/server-github")
                env = @{
                    GITHUB_PERSONAL_ACCESS_TOKEN = $env:GITHUB_TOKEN
                }
            }
            "brave-search" = @{
                command = "npx"
                args = @("-y", "@modelcontextprotocol/server-brave-search")
                env = @{
                    BRAVE_API_KEY = $env:BRAVE_API_KEY
                }
            }
            fetch = @{
                command = "npx"
                args = @("-y", "@modelcontextprotocol/server-fetch")
            }
            postgres = @{
                command = "npx"
                args = @("-y", "@modelcontextprotocol/server-postgres")
                env = @{
                    NEON_DSN = $env:NEON_DSN
                }
            }
            "puppeteer" = @{
                command = "npx"
                args = @("-y", "@modelcontextprotocol/server-puppeteer")
            }
            memory = @{
                command = "npx"
                args = @("-y", "@modelcontextprotocol/server-memory")
            }
            "sequential-thinking" = @{
                command = "npx"
                args = @("-y", "@modelcontextprotocol/server-sequential-thinking")
            }
            time = @{
                command = "npx"
                args = @("-y", "@modelcontextprotocol/server-time")
            }
            "universal-second-brain" = @{
                command = "X:/second-brain-kb/.venv/Scripts/python.exe"
                args = @("X:/second-brain-kb/mcp_server_v4.py")
                env = @{
                    NEON_DSN = $env:NEON_DSN
                    OLLAMA_EMBED_URL = "http://127.0.0.1:11434/api/embed"
                    EMBED_MODEL = "nomic-embed-text"
                }
                description = "Second Brain v4 MCP - Vector search + Agent pipeline + File ops"
            }
        }
    }
    $newConfig | ConvertTo-Json -Depth 10 | Set-Content $mcpAllPath
    Write-Host "  Mcp-All.json created" -ForegroundColor Green
}

# Setup opencode.json entry
Write-Host "Configuring opencode.json..." -ForegroundColor Green
$opencodePath = "$env:USERPROFILE\.config\opencode\opencode.json"
if (Test-Path $opencodePath) {
    $content = Get-Content $opencodePath -Raw | ConvertFrom-Json
    if (-not ($json.mcp.'second-brain-v4')) {
        $json.mcp.'second-brain-v4' = @{
            type = "local"
            enabled = $true
            command = @(
                "X:/second-brain-kb/.venv/Scripts/python.exe"
                "X:/second-brain-kb/mcp_server_v4.py"
            )
        }
        $json | ConvertTo-Json -Depth 10 | Set-Content $opencodePath
        Write-Host "  opencode.json updated" -ForegroundColor Cyan
    } else {
        Write-Host "  opencode.json already configured" -ForegroundColor Yellow
    }
} else {
    Write-Host "  Creating new opencode.json..." -ForegroundColor Cyan
    $opencodeDir = "$env:USERPROFILE\.config\opencode"
    if (-not (Test-Path $opencodeDir)) {
        New-Item -ItemType Directory -Path $opencodeDir | Out-Null
    }
    $initConfig = @{
        mcp = @{
            "second-brain-v4" = @{
                type = "local"
                enabled = $true
                command = @(
                    "X:/second-brain-kb/.venv/Scripts/python.exe"
                    "X:/second-brain-kb/mcp_server_v4.py"
                )
            }
        }
    }
    $initConfig | ConvertTo-Json -Depth 10 | Set-Content $opencodePath
    Write-Host "  opencode.json created" -ForegroundColor Green
}

Write-Host "Setup Complete!" -ForegroundColor Green
