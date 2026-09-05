# Second Brain KB Shortcut Creator
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Second Brain KB Shortcut Creator" -ForegroundColor White -BackgroundColor DarkCyan
Write-Host "=" * 60 -ForegroundColor Cyan

# Get desktop path
$desktop = [Environment]::GetFolderPath('Desktop')
Write-Host "Desktop path: $desktop" -ForegroundColor Yellow

# Define paths
$shortcutName = "Second Brain KB.lnk"
$shortcutPath = Join-Path $desktop $shortcutName
$targetPath = "X:\second-brain-kb\launch.bat"

Write-Host "Target: $targetPath" -ForegroundColor Cyan
Write-Host "Shortcut will be: $shortcutPath" -ForegroundColor Yellow

# Create WScript.Shell object
Write-Host "Creating shortcut..." -ForegroundColor Green
try {
    $shell = New-Object -ComObject WScript.Shell
    
    # Create the shortcut
    $shortcut = $shell.CreateShortcut($shortcutPath)
    
    # Set properties
    $shortcut.TargetPath = $targetPath
    $shortcut.WorkingDirectory = "X:\second-brain-kb"
    $shortcut.Description = "Second Brain KB v4 - API + Frontend Dashboard"
    
    # Save the shortcut
    $shortcut.Save()
    
    Write-Host "Shortcut created successfully!" -ForegroundColor Green
    Write-Host "Location: $shortcutPath" -ForegroundColor Cyan
    
    # Verify
    Write-Host "--- Verification ---" -ForegroundColor Yellow
    Write-Host "Target: $($shortcut.TargetPath)" -ForegroundColor Green
    Write-Host "Working Directory: $($shortcut.WorkingDirectory)" -ForegroundColor Green
    Write-Host "Description: $($shortcut.Description)" -ForegroundColor Green
}
catch {
    Write-Host "Error creating shortcut: $_" -ForegroundColor Red
}