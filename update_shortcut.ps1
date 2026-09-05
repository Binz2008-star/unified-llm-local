$wshell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcut = $wshell.CreateShortcut("$desktop\Unified LLM Local.lnk")
$shortcut.TargetPath = 'cmd.exe'
$shortcut.Arguments = '/c cd /d X:\unified-llm-local && docker compose -f docker-compose.v4.yml up -d && pause'
$shortcut.WorkingDirectory = 'X:\unified-llm-local'
$shortcut.Description = 'Start Unified LLM Local via Docker'
$shortcut.IconLocation = 'cmd.exe,0'
$shortcut.Save()
Write-Host 'Shortcut updated!'
