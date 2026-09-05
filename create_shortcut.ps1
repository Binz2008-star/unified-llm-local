$wshell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcut = $wshell.CreateShortcut("$desktop\Unified LLM Local.lnk")
$shortcut.TargetPath = 'cmd.exe'
$shortcut.Arguments = '/c cd /d X:\unified-llm-local && start "API Server" python api.py && start "Dashboard" cmd /c cd X:\unified-llm-local\ai-dashboard && node dist/server.js && timeout /t 3 /nobreak >nul && start http://localhost:3000'
$shortcut.WorkingDirectory = 'X:\unified-llm-local'
$shortcut.Description = 'Start Unified LLM Local - All Systems'
$shortcut.IconLocation = 'cmd.exe,0'
$shortcut.Save()
Write-Host 'Shortcut created on Desktop!'
