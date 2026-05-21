# setup_taskscheduler.ps1
# タスクスケジューラにToDoアプリを登録（ログイン時にバックグラウンド自動起動）
# 管理者権限は不要です。PowerShellで実行してください。

$taskName   = "ToDoApp_Panel"
$scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$batchPath  = Join-Path $scriptDir "start_server.bat"

# 既存タスクを削除してから再登録
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

$action   = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$batchPath`"" `
    -WorkingDirectory $scriptDir

$trigger  = New-ScheduledTaskTrigger -AtLogon

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew `
    -Hidden

Register-ScheduledTask `
    -TaskName $taskName `
    -Action   $action `
    -Trigger  $trigger `
    -Settings $settings `
    -RunLevel Limited `
    -Force | Out-Null

Write-Host ""
Write-Host "✅ タスクスケジューラに '$taskName' を登録しました。" -ForegroundColor Green
Write-Host "   次回ログイン時から自動起動します。"
Write-Host ""
Write-Host "今すぐ起動する場合:"
Write-Host "   Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor Cyan
Write-Host ""
Write-Host "停止する場合:"
Write-Host "   Stop-ScheduledTask  -TaskName '$taskName'" -ForegroundColor Yellow
Write-Host ""
Write-Host "アプリURL: http://localhost:5006"
