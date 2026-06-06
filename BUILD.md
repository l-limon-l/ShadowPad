# Сборка и «тихий» запуск — пошаговая инструкция

---

## 1. Способы тихого запуска (без сборки)

### Вариант A — VBS-лаунчер (рекомендуется)

Двойной клик по `launch.vbs`. Всё. Никакой консоли, никакого мелькания.

Для автозапуска при входе в Windows:
1. `Win+R` → `shell:startup`
2. Скопировать ярлык на `launch.vbs` в открывшуюся папку

### Вариант B — BAT-файл

Двойной клик по `start.bat` — консоль мелькнёт на долю секунды и закроется.

### Вариант C — PowerShell (one-liner)

```powershell
Start-Process pythonw.exe -ArgumentList "C:\path\to\sticky_note.py" -WindowStyle Hidden
```

---

## 2. Сборка в EXE через PyInstaller (максимальная скрытность)

### Установка PyInstaller

```bash
pip install pyinstaller
```

### Команда сборки

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

**Что это делает:**
- `--name "RuntimeBroker"` — процесс в Диспетчере задач показывает `RuntimeBroker.exe`
- `--noconsole` — без консоли
- `--onefile` — один .exe файл
- `--icon=NONE` — стандартная иконка (не Python)
- `--add-data "notes;notes"` — включить папку заметок

### Альтернативные имена процесса

| Имя | Описание |
|-----|----------|
| `RuntimeBroker` | Системный процесс Windows (безобидно) |
| `SearchUI` | Поиск Windows |
| `SecurityHealthSystray` | Центр безопасности |
| `TextInputHost` | Ввод текста |
| `SettingSyncHost` | Синхронизация настроек |

### С системной иконкой

```bash
pyinstaller ^
  --name "RuntimeBroker" ^
  --noconsole ^
  --onefile ^
  --icon="%SystemRoot%\System32\shell32.dll,1" ^
  sticky_note.py
```

---

## 3. Расписание автозапуска через Task Scheduler

Для максимальной скрытности — запуск через планировщик задач:

```powershell
$action  = New-ScheduledTaskAction -Execute "pythonw.exe" `
           -Argument '"C:\path\to\sticky_note.py"'
$trigger = New-ScheduledTaskTrigger -AtLogon
$settings = New-ScheduledTaskSettingsSet -Hidden

Register-ScheduledTask -TaskName "WindowsRuntimeBroker" `
  -Action $action -Trigger $trigger -Settings $settings `
  -Description "Windows Runtime Component Manager"
```

Задача будет запускаться при входе в систему и не будет видна среди обычных программ автозагрузки.

---

## 4. Горячие клавиши

| Хоткей | Действие |
|--------|----------|
| `Ctrl+Shift+H` | Показать / скрыть окно (с fade-анимацией) |
| `Ctrl+Shift+Q` | **PANIC** — мгновенное убийство процесса |
| `Ctrl+B` | Жирный текст (toggle) |
| `Ctrl+I` | Курсив (toggle) |
| `Ctrl+1..5` | Выделение цветом (жёлтый / красный / зелёный / голубой / фиолетовый) |
| `Ctrl+0` | Сброс форматирования |
| `Ctrl+F` | Поиск по тексту |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Enter` / `↓` | Следующее совпадение (в поиске) |
| `Shift+Enter` / `↑` | Предыдущее совпадение |
| `Escape` | Закрыть поиск |

---

## 5. Настройки `config.json`

```json
{
  "geometry": "340x280+80+80",
  "alpha": 0.93,
  "current": "Заметка 1",
  "font_size": 11,
  "panel_open": false,
  "auto_hide_on_focus_loss": false
}
```

| Поле | Описание |
|------|----------|
| `auto_hide_on_focus_loss` | `true` — окно скрывается при клике мимо него |
| `alpha` | Прозрачность (0.2 — 1.0) |
| `panel_open` | Запомнить состояние боковой панели |

---

## 6. Защита от обнаружения — чеклист

- [x] Окно скрыто от захвата экрана (`WDA_EXCLUDEFROMCAPTURE`)
- [x] Нет в Alt+Tab (`WS_EX_TOOLWINDOW`)
- [x] Нет в панели задач (`WS_EX_TOOLWINDOW` + `~WS_EX_APPWINDOW`)
- [x] Нет консоли (pythonw.exe / PyInstaller --noconsole)
- [x] Процесс маскируется под системный (PyInstaller --name)
- [x] Panic button мгновенно убивает процесс
- [x] Fade-in/out при показе/скрытии
- [x] Одиночный экземпляр (mutex)
- [x] Авто-скрытие при потере фокуса (опционально)
