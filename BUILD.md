# Build and Stealth Launch Instructions

---

## 1. Stealth Launch Methods (Without Building)

### Option A — VBS Launcher (Recommended)

Double-click `launch.vbs`. That's it. No console window, no flashing.

For auto-start on Windows login:
1. Press `Win+R` → type `shell:startup`
2. Copy a shortcut of `launch.vbs` into the opened folder.

### Option B — BAT File

Double-click `start.bat` — a console window will flash for a fraction of a second and close.

### Option C — PowerShell (One-liner)

```powershell
Start-Process pythonw.exe -ArgumentList "C:\path\to\sticky_note.py" -WindowStyle Hidden
```

---

## 2. Building an EXE via PyInstaller (Maximum Stealth)

### Install PyInstaller

```bash
pip install pyinstaller
```

### Build Command

```bash
pyinstaller ^
  --name "RuntimeBroker" ^
  --noconsole ^
  --onefile ^
  --icon=NONE ^
  --add-data "notes;notes" ^
  --distpath . ^
  sticky_note.py
```

**What this does:**
- `--name "RuntimeBroker"` — The process shows up as `RuntimeBroker.exe` in Task Manager.
- `--noconsole` — Runs without a command prompt.
- `--onefile` — Packages everything into a single `.exe` file.
- `--icon=NONE` — Uses a standard Windows icon instead of the Python logo.
- `--add-data "notes;notes"` — Includes the notes directory.

### Alternative Process Names

| Name | Description |
|------|-------------|
| `RuntimeBroker` | Windows system process (harmless) |
| `SearchUI` | Windows Search |
| `SecurityHealthSystray` | Security Center |
| `TextInputHost` | Text Input |
| `SettingSyncHost` | Settings Sync |

### With System Icon

```bash
pyinstaller ^
  --name "RuntimeBroker" ^
  --noconsole ^
  --onefile ^
  --icon="%SystemRoot%\System32\shell32.dll,1" ^
  sticky_note.py
```

---

## 3. Scheduled Auto-Start via Task Scheduler

For maximum stealth — launch via Task Scheduler:

```powershell
$action  = New-ScheduledTaskAction -Execute "pythonw.exe" `
           -Argument '"C:\path\to\sticky_note.py"'
$trigger = New-ScheduledTaskTrigger -AtLogon
$settings = New-ScheduledTaskSettingsSet -Hidden

Register-ScheduledTask -TaskName "WindowsRuntimeBroker" `
  -Action $action -Trigger $trigger -Settings $settings `
  -Description "Windows Runtime Component Manager"
```

The task will start on login and will not be visible among standard startup programs.

---

## 4. Hotkeys

| Hotkey | Action |
|--------|--------|
| `Ctrl+Shift+H` | Show / hide window (with fade animation) |
| `Ctrl+Shift+Q` | **PANIC** — instantly kill the process |
| `Ctrl+B` | Bold text (toggle) |
| `Ctrl+I` | Italic text (toggle) |
| `Ctrl+1..5` | Highlight color (Yellow / Red / Green / Blue / Purple) |
| `Ctrl+0` | Clear formatting |
| `Ctrl+F` | Text search |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Enter` / `↓` | Next match (in search) |
| `Shift+Enter` / `↑`| Previous match |
| `Escape` | Close search |

---

## 5. `config.json` Settings

```json
{
  "geometry": "340x280+80+80",
  "alpha": 0.93,
  "current": "Note 1",
  "font_size": 11,
  "panel_open": false,
  "auto_hide_on_focus_loss": false
}
```

| Field | Description |
|-------|-------------|
| `auto_hide_on_focus_loss` | `true` — window hides when you click outside of it |
| `alpha` | Transparency (0.2 — 1.0) |
| `panel_open` | Remember sidebar panel state |

---

## 6. Stealth Checklist

- [x] Window excluded from screen capture (`WDA_EXCLUDEFROMCAPTURE`)
- [x] Hidden from Alt+Tab (`WS_EX_TOOLWINDOW`)
- [x] Hidden from Taskbar (`WS_EX_TOOLWINDOW` + `~WS_EX_APPWINDOW`)
- [x] No console window (pythonw.exe / PyInstaller --noconsole)
- [x] Process masked as a system process (PyInstaller --name)
- [x] Panic button instantly kills the process
- [x] Fade-in/out transitions when showing/hiding
- [x] Single instance only (mutex)
- [x] Auto-hide on focus loss (optional)
