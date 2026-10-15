# HDMI Audio Light

**Plugged your laptop back into the TV and the sound won't come through HDMI?** It plays from the laptop speakers instead, or the TV is missing from the sound output list, until you dig into Device Manager or reboot.

This is a tiny Windows 11 taskbar widget for that problem. A light shows whether HDMI audio is working (green) or has crashed (red). One click brings it back, no reboot and no Device Manager.

```
 ● HDMI
```

| Light | Meaning |
|---|---|
| 🟢 green | controller OK |
| 🔴 red | crashed (Code 43 or other problem) — click to reset |
| 🟡 amber | resetting |
| ⚪ gray | controller not found |

## The problem

**What you notice:** you unplug the TV, later plug it back in, and the picture works but the sound doesn't. The TV doesn't appear as a sound output, or picking it does nothing.

**What's actually happening:** on laptops with two graphics chips (this was built on a ThinkPad P72 with an NVIDIA Quadro P600), the HDMI port is run by the NVIDIA chip. When the TV is unplugged, that chip puts its sound part to sleep to save power, and sometimes it wakes up broken. Windows notices, gives up on it, and leaves it off.

**How to confirm it:** in Device Manager → *System devices*, one of the two **High Definition Audio Controller** entries has a yellow warning triangle. Its properties say *"Windows has stopped this device because it has reported problems. (Code 43)."*

**The fix:** turning that device off and on again (Disable, then Enable) brings the sound back every time. New drivers haven't fixed the underlying problem. This widget does the off-and-on for you with one click.

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
