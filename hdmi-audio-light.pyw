# HDMI Audio Light — a taskbar status light + reset button for the ThinkPad P72's HDMI audio.
# Copyright (c) 2026 Formstone Castle LLC — https://formstonecastle.com
# Created by Michael Bowman for Formstone Castle LLC, October 2026.
# Licensed under PolyForm Noncommercial 1.0.0 (see LICENSE and NOTICE).
# Keep this notice in all copies and modified versions. Commercial use needs a
# separate agreement. Courtesy request: tell us what you build (mike@formstonecastle.com).

"""HDMI audio light -- a tiny widget living inside the Windows taskbar.

The P72's HDMI port hangs off the NVIDIA Quadro P600. After a TV
unplug/replug, the GPU's HDMI audio controller often wakes up broken
(Device Manager: Code 43) until it is disabled and re-enabled.

This widget shows that controller's health and resets it on click:
    green = OK      red = crashed      amber = resetting      gray = not found

Click path: if the "Fix HDMI Audio" scheduled task exists (see
Install-NoUac.ps1), it runs that -- no UAC prompt. Otherwise it runs
Fix-HdmiAudio.ps1 elevated, which costs one UAC click.

Docking uses the same trick as the Claude 5h Clock (re-parent into
Shell_TrayWnd + WS_EX_LAYERED). It parks itself just left of any other
Tk widget already docked there, so the two never overlap.

Pure stdlib (tkinter + ctypes) -- no pip installs needed.
"""

import ctypes
import subprocess
import sys
import tkinter as tk
from ctypes import wintypes
from pathlib import Path

# ---- Tunables --------------------------------------------------------------
POLL_MS = 3_000            # re-check the controller (cheap: no subprocess)
TICK_MS = 1_000            # check the taskbar / re-dock
FAST_POLL_MS = 300         # after a click, check this often so green shows ASAP
MIN_BUSY_MS = 1_000        # ...but stay amber at least this long (the old
                           # "ok" can linger a beat before disable lands)
MAX_BUSY_MS = 20_000       # give up waiting and show whatever state it's in
RIGHT_GAP = 245            # fallback spot if no other widget is docked
                           # (same as the 5h clock's: clears tray + clock)
SIBLING_GAP = 14           # px between us and the widget to our right
TASKBAR_BG = "#1c1c1c"     # Win11 dark-mode taskbar color (28,28,28)
FG = "#ffffff"
LIGHT = {"ok": "#3fb950", "error": "#f85149", "busy": "#d29922", "missing": "#6e7681"}
FONT_PX = 14
DOT = 12

TASK_NAME = "Fix HDMI Audio"
FIX_SCRIPT = Path(__file__).with_name("Fix-HdmiAudio.ps1")
NVIDIA = "PCI\\VEN_10DE"
HDA_SERVICE = "HDAudBus"   # the GPU itself is also VEN_10DE; its audio half
                           # is the one running the HD Audio bus driver
NO_WINDOW = 0x08000000     # CREATE_NO_WINDOW: no console flash on click

# ---- Win32 plumbing ----------------------------------------------------------
user32 = ctypes.windll.user32
user32.FindWindowW.restype = wintypes.HWND
user32.GetParent.restype = wintypes.HWND
user32.GetParent.argtypes = (wintypes.HWND,)
user32.SetWindowLongPtrW.argtypes = (wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t)
user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.GetWindowLongPtrW.argtypes = (wintypes.HWND, ctypes.c_int)
GWL_STYLE, GWL_EXSTYLE = -16, -20
WS_CHILD, WS_POPUP = 0x40000000, 0x80000000
WS_EX_LAYERED, LWA_ALPHA = 0x00080000, 0x2
SWP_NOACTIVATE, SWP_SHOWWINDOW = 0x0010, 0x0040
ENUM_PROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

try:  # real pixels, so our coordinates match the taskbar's
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except OSError:
    pass


def taskbar():
    return user32.FindWindowW("Shell_TrayWnd", None)


def client_size(hwnd):
    r = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(r))
    return r.right, r.bottom


def window_rect(hwnd):
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r


def leftmost_sibling(bar, me):
    """Left edge (taskbar coords) of the leftmost other Tk widget docked in the taskbar, or None."""
    lefts = []
    cls = ctypes.create_unicode_buffer(64)

    def visit(h, _):
        if h != me and user32.GetParent(h) == bar and user32.IsWindowVisible(h):
            user32.GetClassNameW(h, cls, 64)
            if cls.value == "TkTopLevel":
                lefts.append(window_rect(h).left)
        return True

    user32.EnumChildWindows(bar, ENUM_PROC(visit), 0)
    return min(lefts) - window_rect(bar).left if lefts else None


# ---- Device status (Configuration Manager API -- no PowerShell needed) ------
cfg = ctypes.WinDLL("cfgmgr32")
CR_SUCCESS = 0
CM_GETIDLIST_FILTER_ENUMERATOR, CM_GETIDLIST_FILTER_PRESENT = 0x1, 0x100
CM_DRP_SERVICE = 0x5


def controller_state():
    """'ok', 'error', or 'missing' for the NVIDIA HDMI audio controller."""
    flags = CM_GETIDLIST_FILTER_ENUMERATOR | CM_GETIDLIST_FILTER_PRESENT
    size = wintypes.ULONG()
    if cfg.CM_Get_Device_ID_List_SizeW(ctypes.byref(size), "PCI", flags) != CR_SUCCESS:
        return "missing"
    buf = ctypes.create_unicode_buffer(size.value)
    if cfg.CM_Get_Device_ID_ListW("PCI", buf, size, flags) != CR_SUCCESS:
        return "missing"
    ids = ctypes.wstring_at(ctypes.addressof(buf), size.value).split("\0")

    for dev_id in ids:
        if not dev_id.upper().startswith(NVIDIA):
            continue
        node = wintypes.DWORD()
        if cfg.CM_Locate_DevNodeW(ctypes.byref(node), dev_id, 0) != CR_SUCCESS:
            continue
        svc = ctypes.create_unicode_buffer(64)
        length = wintypes.ULONG(ctypes.sizeof(svc))
        cfg.CM_Get_DevNode_Registry_PropertyW(node, CM_DRP_SERVICE, None, svc,
                                              ctypes.byref(length), 0)
        if svc.value.lower() != HDA_SERVICE.lower():
            continue
        status, problem = wintypes.ULONG(), wintypes.ULONG()
        cfg.CM_Get_DevNode_Status(ctypes.byref(status), ctypes.byref(problem), node, 0)
        return "error" if problem.value else "ok"
    return "missing"


def run_fix():
    """Reset the controller: the no-UAC task if installed, else one UAC prompt."""
    have_task = subprocess.run(["schtasks", "/query", "/tn", TASK_NAME],
                               capture_output=True, creationflags=NO_WINDOW).returncode == 0
    if have_task:
        subprocess.Popen(["schtasks", "/run", "/tn", TASK_NAME], creationflags=NO_WINDOW)
    else:
        # Hidden window (0) + -Quiet: the light itself reports the result.
        args = f'-NoProfile -ExecutionPolicy Bypass -File "{FIX_SCRIPT}" -Quiet'
        ctypes.windll.shell32.ShellExecuteW(None, "runas", "pwsh", args, None, 0)


# ---- Widget ----------------------------------------------------------------
class Light:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.configure(bg=TASKBAR_BG)
        self.font = ("Segoe UI", -FONT_PX)
        self.state = controller_state()
        self.busy = False

        _, self.bar_h = client_size(taskbar()) if taskbar() else (0, 48)
        self.cv = tk.Canvas(self.root, bg=TASKBAR_BG, highlightthickness=0,
                            height=self.bar_h, width=80, cursor="hand2")
        self.cv.pack()
        self.cv.bind("<Button-1>", self.click)
        self.parent = None

        self.paint()
        self.poll()
        self.tick()
        self.root.mainloop()

    def paint(self):
        cv = self.cv
        cv.delete("all")
        cy = self.bar_h / 2
        color = LIGHT["busy" if self.busy else self.state]
        cv.create_oval(2, cy - DOT / 2, 2 + DOT, cy + DOT / 2, fill=color, width=0)
        t = cv.create_text(DOT + 8, cy, text="HDMI", fill=FG, font=self.font, anchor="w")
        self.width = int(cv.bbox(t)[2] + 2)
        cv.configure(width=self.width)

    def click(self, _event):
        if self.busy:
            return          # one reset at a time
        self.busy = True
        self.paint()
        run_fix()
        self.root.after(FAST_POLL_MS, self.watch, FAST_POLL_MS)

    def watch(self, elapsed):
        """Fast-poll after a click; go back to normal the moment it's healthy."""
        state = controller_state()
        if (state == "ok" and elapsed >= MIN_BUSY_MS) or elapsed >= MAX_BUSY_MS:
            self.busy = False
            self.state = state
            self.paint()
        else:
            self.root.after(FAST_POLL_MS, self.watch, elapsed + FAST_POLL_MS)

    # Keep ourselves glued inside the taskbar. If Explorer restarts, the
    # taskbar gets a new handle and we re-attach to it.
    def dock(self):
        bar = taskbar()
        if not bar:
            return
        me = int(self.root.wm_frame(), 16)
        if self.parent != bar or user32.GetParent(me) != bar:
            style = user32.GetWindowLongPtrW(me, GWL_STYLE)
            user32.SetWindowLongPtrW(me, GWL_STYLE, (style | WS_CHILD) & ~WS_POPUP)
            # Win11's XAML taskbar covers plain child windows; a layered
            # window gets its own DWM surface and shows on top.
            ex = user32.GetWindowLongPtrW(me, GWL_EXSTYLE)
            user32.SetWindowLongPtrW(me, GWL_EXSTYLE, ex | WS_EX_LAYERED)
            user32.SetLayeredWindowAttributes(me, 0, 255, LWA_ALPHA)
            user32.SetParent(me, bar)
            self.parent = bar
        bar_w, self.bar_h = client_size(bar)
        sib = leftmost_sibling(bar, me)
        x = (sib - SIBLING_GAP if sib is not None else bar_w - RIGHT_GAP) - self.width
        user32.SetWindowPos(me, None, x, 1, self.width, self.bar_h - 1,
                            SWP_NOACTIVATE | SWP_SHOWWINDOW)

    def poll(self):
        if not self.busy:
            new = controller_state()
            if new != self.state:
                self.state = new
                self.paint()
        self.root.after(POLL_MS, self.poll)

    def tick(self):
        self.dock()
        self.root.after(TICK_MS, self.tick)


if __name__ == "__main__":
    # One instance only: a named mutex survives as long as we do.
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    ctypes.set_last_error(0)
    kernel32.CreateMutexW(None, False, "FscHdmiAudioLight")
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        sys.exit(0)
    Light()
