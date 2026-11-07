$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\scripts\run_lis_sync.ps1"
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 3am
Register-ScheduledTask -TaskName "LegalHub_LIS_Sync" -Action $action -Trigger $trigger -Description "Legal Hub Local LIS Weekly Sync (Disabled)" -Force
Disable-ScheduledTask -TaskName "LegalHub_LIS_Sync"
Get-ScheduledTask -TaskName "LegalHub_LIS_Sync" | Format-List TaskName, State, Description

