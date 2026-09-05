@echo off
cd /d "%~dp0"

echo ==========================================
echo Second Brain KB - Full Dashboard Setup a-z
echo ==========================================
echo.

:: Step 1: Verify API is running
echo Step 1: Checking FastAPI backend...
if not exist .\api.py (
    echo ERROR: api.py not found!
    goto error
)
echo API script found.

:: Step 2: Verify ai-dashboard exists
echo Step 2: Checking AI Dashboard...
if not exist .\ai-dashboard (
    echo ERROR: ai-dashboard directory not found!
    goto error
)
echo AI Dashboard directory found.

:: Step 3: Install npm dependencies
echo Step 3: Installing npm dependencies...
cd .\ai-dashboard
if not exist node_modules\install_success marker 2>nul (
    npm install --legacy-peer-deps 2>&1 | find /i "ok" > nul
    if %errorlevel% equ 0 (
        echo marker > node_modules\install_success marker
        echo npm dependencies installed.
    ) else (
        echo WARNING: npm install had issues, continuing anyway...
    )
) else (
    echo npm dependencies already installed.
)
cd ..\..

:: Step 4: Verify .env file
echo Step 4: Checking environment configuration...
if not exist .env (
    echo WARNING: .env file not found, creating template...
    echo NEON_DSN=postgresql://neondb_owner:npg_Iwmn6zQlT5Jt@ep-empty-paper-avokj61h-pooler.c-11.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require > .env
    echo OLLAMA_EMBED_URL=http://127.0.0.1:11434/api/embed >> .env
    echo OLLAMA_CHAT_URL=http://127.0.0.1:11434/api/chat >> .env
    echo EMBED_MODEL=nomic-embed-text >> .env
    echo CHAT_MODEL=deepseek-r1:14b >> .env
)
echo Environment configured.

:: Step 5: Start the backend
echo Step 5: Starting FastAPI backend...
start /B python api.py > NUL 2>&1
timeout /T 3 /nobreak > nul
echo FastAPI starting on port 8000...

:: Step 6: Start the frontend
echo Step 6: Starting frontend dashboard...
cd ai-dashboard
start /B npm run dev 2>&1 | find /i "vite" > nul
timeout /T 5 /nobreak > nul
echo Frontend starting on port 3000...

:: Step 7: Open browser
echo Step 7: Opening dashboard in browser...
timeout /T 6 /nobreak > nul
start "" http://localhost:3000
echo Dashboard opening in default browser...

echo.
echo ==========================================
echo Second Brain KB is now running!
echo ==========================================
echo.
echo Access points:
echo - API:      http://localhost:8000/status
echo - Dashboard: http://localhost:3000
echo.
echo Press Ctrl+C to stop or close this window.
echo.
pause

goto end

:error
echo.
echo ==========================================
echo ERROR: Failed to set up Second Brain KB
echo ==========================================
echo.
echo Required files missing.
echo.
echo Make sure you are in the Second Brain KB directory.
echo.
pause
:end