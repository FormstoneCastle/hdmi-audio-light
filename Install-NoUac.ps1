# Install-NoUac.ps1 — one-time setup so "Fix HDMI Audio" runs without a UAC prompt.
# Copyright (c) 2026 Formstone Castle LLC — https://formstonecastle.com
# Created by Michael Bowman. Licensed under PolyForm Noncommercial 1.0.0 (see LICENSE and NOTICE).
#
# Run elevated ONCE:  sudo pwsh -NoProfile -File Install-NoUac.ps1
#
# Why a scheduled task: tasks marked "run with highest privileges" are approved
# when created, then can be started by the normal user with no prompt.
# Why Program Files: an admin-level task must only run a file that admins can
# change — otherwise anything on the laptop could edit it and gain admin rights.

$dest = 'C:\Program Files\FixHdmiAudio'
New-Item -ItemType Directory -Force $dest | Out-Null
Copy-Item "$PSScriptRoot\Fix-HdmiAudio.ps1" $dest -Force

$pwsh   = (Get-Command pwsh).Source
$action = New-ScheduledTaskAction -Execute $pwsh `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$dest\Fix-HdmiAudio.ps1`" -Quiet"
# Interactive logon = runs in Mike's session. Hidden + -Quiet: the taskbar light shows the result.
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive -RunLevel Highest
$settings  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

# No trigger: it only runs when the shortcut asks.
Register-ScheduledTask -TaskName 'Fix HDMI Audio' -Action $action -Principal $principal `
    -Settings $settings -Force | Out-Null
Write-Host "Task 'Fix HDMI Audio' registered." -ForegroundColor Green
