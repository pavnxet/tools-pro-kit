# scan-folder.ps1 – Manual secret scanner
param(
    [string]$FolderPath
)

if (-not $FolderPath) {
    $FolderPath = Read-Host "Enter the full path of the folder to scan"
}

if (-not (Test-Path $FolderPath)) {
    Write-Host "❌ Folder not found: $FolderPath" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "🔍 Scanning for secrets in: $FolderPath" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Run Gitleaks directly (assumes gitleaks.exe is in PATH)
& gitleaks detect --source $FolderPath --no-git --verbose

Write-Host "`n✅ Scan finished." -ForegroundColor Yellow
Read-Host "Press Enter to close"
