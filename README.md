# HDMI Audio Light

A tiny Windows 11 taskbar widget for the **NVIDIA HDMI audio "Code 43" crash**: a status light that shows whether the GPU's HDMI audio controller is healthy, and resets it with one click.

```
 ● HDMI
```

| Light | Meaning |
|---|---|
| 🟢 green | controller OK |
| 🔴 red | crashed (Code 43 or other problem) — click to reset |
| 🟡 amber | resetting |
| ⚪ gray | controller not found |

## The bug

On hybrid-graphics laptops (built on a ThinkPad P72 / Quadro P600) the HDMI port is wired to the NVIDIA GPU. When a TV or monitor is unplugged, the GPU powers its audio controller down; on replug it often wakes up broken. Device Manager shows a **High Definition Audio Controller** with a yellow triangle and **Code 43**, and HDMI sound is gone. Driver swaps haven't fixed it. Disabling and re-enabling the controller does, every time. This widget does that for you.

## Files

| File | What |
|---|---|
| `hdmi-audio-light.pyw` | the taskbar widget |
| `Fix-HdmiAudio.ps1` | the reset: disables + re-enables the NVIDIA controller. Runs standalone too |
| `Install-NoUac.ps1` | optional one-time setup so clicks skip the UAC prompt |

## Requirements

- Windows 11 (dark taskbar)
- Python 3.10+ (stdlib only — tkinter + ctypes, no pip installs)
- PowerShell 7 (`pwsh`)

## Install

1. Put the folder anywhere.
2. Run `hdmi-audio-light.pyw` (double-click, or `pythonw hdmi-audio-light.pyw`).
3. Auto-start: put a shortcut to it in `shell:startup`.

Each click asks for admin (UAC), because turning a device off and on needs it.

### Optional: no UAC prompt

Run once, elevated:

```
sudo pwsh -NoProfile -ExecutionPolicy Bypass -File Install-NoUac.ps1
```

This copies the reset script into `C:\Program Files\FixHdmiAudio\` (admin-only, so nothing can tamper with it) and registers a scheduled task, **Fix HDMI Audio**, that runs it with highest privileges. The widget detects the task and uses it — no prompt.

Undo: `sudo schtasks /delete /tn "Fix HDMI Audio" /f`

## How it works

- **Status:** reads the controller's state straight from the Windows Configuration Manager API (`cfgmgr32`) every 3 seconds — no PowerShell, no polling cost. It finds the controller as the NVIDIA PCI device (`VEN_10DE`) running the `HDAudBus` driver, so it survives Windows renumbering the device.
- **Docking:** same trick as [Claude 5h Clock](https://github.com/FormstoneCastle/claude-5h-clock) — the window is re-parented into the taskbar (`Shell_TrayWnd`) as a layered window. It parks itself just left of any other Tk widget already docked there, so the two sit side by side.
- Not an officially supported Windows API — a future feature update could break the docking.

## Tuning

| Name | Default | What |
|---|---|---|
| `RIGHT_GAP` | `245` | px from the taskbar's right edge when no other widget is docked |
| `SIBLING_GAP` | `14` | px between this and a neighboring widget |
| `TASKBAR_BG` | `#1c1c1c` | background; match your taskbar color |
| `POLL_MS` | `3000` | how often the status is checked |

## Limits

- Green means the **controller** is healthy — not that a TV is connected or selected as the output device.

## Credits

Created by **Michael Bowman** for **[Formstone Castle LLC](https://formstonecastle.com)**, 2026.
Licensed under PolyForm Noncommercial 1.0.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).

Not affiliated with NVIDIA, Lenovo, or Microsoft.
