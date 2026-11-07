# scripts/install_local_schedule.ps1
# Prompt 4: Local Windows Task Scheduler setup for LawPlayer updates.
# Rate limited, daily cap 600, runs locally only (never remote).

param (
    [switch]$Confirm
)

$TaskName = "LegalHub_LawplayerDailyUpdate"
$WorkspaceDir = "c:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub"
$PythonExe = "python.exe"
$Arguments = "backend/updater/cli.py --source lawplayer --apply"
$DailyTime = "02:00"
$LogPath = "$WorkspaceDir\logs\update"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Legal Hub - LawPlayer Local Task Scheduler Configuration" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Task Name:        $TaskName"
Write-Host "Schedule:         Daily at $DailyTime"
Write-Host "Working Directory:$WorkspaceDir"
Write-Host "Command:          $PythonExe $Arguments"
Write-Host "Daily Request Cap:600 requests max"
Write-Host "Log Output:       $LogPath\<yyyy-MM-dd>.log"
Write-Host "Target Host:      Local Machine Only (Windows)"
Write-Host "Security Policy:  Zero proxy, real User-Agent, immediate abort on 403/429/CAPTCHA"
Write-Host "==========================================================" -ForegroundColor Cyan

if (-not $Confirm) {
    Write-Host "`n[DRY RUN PREVIEW MODE]" -ForegroundColor Yellow
    Write-Host "No system changes have been made." -ForegroundColor Yellow
    Write-Host "To register this scheduled task in Windows Task Scheduler, run:" -ForegroundColor Green
    Write-Host "  .\scripts\install_local_schedule.ps1 -Confirm`n" -ForegroundColor Green
    return
}

# If -Confirm passed, perform actual registration
Write-Host "`n[INSTALLING SCHEDULED TASK] Registering '$TaskName' in Windows Task Scheduler..." -ForegroundColor Cyan

try {
    $Action = New-ScheduledTaskAction -Execute $PythonExe -Argument $Arguments -WorkingDirectory $WorkspaceDir
    $Trigger = New-ScheduledTaskTrigger -Daily -At $DailyTime
    $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Legal Hub LawPlayer Daily Local Sync (Max 600 requests)" -Force | Out-Null
    
    Write-Host "[SUCCESS] Task '$TaskName' successfully registered!" -ForegroundColor Green
    Write-Host "Verification:" -ForegroundColor Cyan
    Get-ScheduledTask -TaskName $TaskName | Format-List TaskName, State
} catch {
    Write-Host "[ERROR] Failed to register scheduled task: $_" -ForegroundColor Red
}

