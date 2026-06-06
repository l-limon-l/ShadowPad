# ShadowPad

**ShadowPad** is an ultra-stealthy, floating sticky notes application designed for maximum discretion. It is engineered to be completely invisible to screen capture tools and screen-sharing software, making it ideal for keeping private notes on your screen during remote sessions, presentations, or strict monitoring environments.

<img width="1260" height="487" alt="image" src="https://github.com/user-attachments/assets/98f17fe0-19b7-40d4-b768-e30d74f90996" />

## ✨ Key Features

*   **Absolute Invisibility**: Utilizes Windows native `WDA_EXCLUDEFROMCAPTURE` flags. The application window (and all its tooltips/menus) is invisible to screen capture software (Snipping Tool, OBS, Teams, Zoom, etc.).
*   **Process Masking**: Includes a stealth launcher (`launch.vbs`) that runs the application under a system-like process name (`RuntimeBroker.exe`), hiding the fact that Python is running.
*   **Panic Key (`Ctrl+Shift+Q`)**: A global hardware-level hotkey that instantly wipes the current note from memory and kills the process without any trace.
*   **Toggle Visibility (`Ctrl+Shift+H`)**: A global hotkey to instantly hide or reveal the note window.
*   **Rich Text Formatting**: Support for Bold, Italic, and 5 highlight colors.
*   **Advanced Undo/Redo**: Features independent Undo/Redo stacks for both text editing and text formatting.
*   **Multi-Note Support**: Create, rename, and manage multiple notes from the built-in sidebar.
*   **Adjustable Opacity**: Tweak the transparency of the window on the fly.
*   **Always on Top**: Keeps your notes above all other windows.

## 🚀 How to Run

### Requirements
*   Windows 10/11
*   Python 3.x

### Launching Stealthily
To launch the application in full stealth mode (process masking + no console window):
1. Double-click **`launch.vbs`**.
2. The application will start silently.

*Alternatively, you can build the application into a standalone executable using PyInstaller. See [BUILD.md](https://github.com/l-limon-l/ShadowPad/blob/main/BUILD.md) for detailed build instructions.*

## ⌨️ Shortcuts & Controls

### Global Hotkeys
*   **`Ctrl+Shift+H`**: Toggle application visibility (fade in/out).
*   **`Ctrl+Shift+Q`**: PANIC KEY. Instantly kills the app.

### In-App Editor
*   **`Ctrl+Z`** / **`Ctrl+Y`**: Undo/Redo text typing.
*   **`Ctrl+B`** / **`Ctrl+I`**: Bold / Italic text.
*   **`Ctrl+1`** to **`Ctrl+5`**: Apply highlight colors.
*   **`Ctrl+0`**: Clear formatting from selected text.
*   **`Ctrl+F`**: Open search bar.

## ⚠️ Disclaimer

ShadowPad is provided for educational and personal productivity purposes. The developer assumes no responsibility for any misuse of this software in environments where it violates academic integrity policies or terms of service.
