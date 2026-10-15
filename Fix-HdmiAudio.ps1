# Fix-HdmiAudio.ps1 — one-click reset for the ThinkPad P72's HDMI audio.
# Copyright (c) 2026 Formstone Castle LLC — https://formstonecastle.com
# Created by Michael Bowman. Licensed under PolyForm Noncommercial 1.0.0 (see LICENSE and NOTICE).
#
# Why: the P72's HDMI port hangs off the NVIDIA Quadro P600. When the TV is
# unplugged, the GPU powers down its audio controller; on replug it often wakes
# up broken (Device Manager: yellow triangle, Code 43). Disabling and
# re-enabling the controller revives it — this script does exactly that,
# so you don't have to dig through Device Manager.

# -Quiet: called by the taskbar light, which shows the result itself,
# so skip the on-screen message and its pause.
param([switch]$Quiet)

# Disable/enable needs admin rights. If we're not elevated, relaunch
# ourselves elevated (one UAC click) and let this copy exit.
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    $fwd = if ($Quiet) { ' -Quiet' } else { '' }
    Start-Process pwsh -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"$fwd"
    exit
}

# Find the controller by vendor (10DE = NVIDIA) + name rather than a hardcoded
# instance ID, so it still works if Windows renumbers the device after an update.
$controller = Get-PnpDevice -Class System -ErrorAction SilentlyContinue |
    Where-Object { $_.InstanceId -like 'PCI\VEN_10DE*' -and $_.FriendlyName -eq 'High Definition Audio Controller' }

if (-not $controller) {
    Write-Host "Couldn't find the NVIDIA HDMI audio controller." -ForegroundColor Red
    Write-Host "The GPU may be asleep — plug in the TV and try again."
    Start-Sleep -Seconds 6
    exit 1
}

# Both calls return only once the driver has finished, so no waits needed.
Disable-PnpDevice -InstanceId $controller.InstanceId -Confirm:$false
Enable-PnpDevice  -InstanceId $controller.InstanceId -Confirm:$false
if ($Quiet) { exit }

$after = (Get-PnpDevice -InstanceId $controller.InstanceId).Status
if ($after -eq 'OK') {
    Write-Host "Signal restored —" -ForegroundColor Green
    Write-Host "the TV sings again. Pick it as output if Windows didn't."
} else {
    Write-Host "Still not happy (status: $after)." -ForegroundColor Yellow
    Write-Host "Try once more, or replug the HDMI cable first."
}
Start-Sleep -Seconds 3
