# GhostType 0.3 — Windows private beta

Local AI text replacement with a compact desktop settings window and notification-area controls. Based on the v0.2 engine. No cloud API or account required. Ollama must already be installed and running.

## Run

1. Stop v0.2 (Ctrl+C in its terminal) to release the shortcuts.
2. Extract this archive to a permanent folder. Do not move it after enabling automatic startup.
3. Double-click `Setup.cmd` once (installs pyperclip and checks Tk). If Windows shows an untrusted-download warning, inspect the source before choosing whether to run it.
4. Double-click `Start GhostType.cmd`. A small console may flash, but the app runs via pythonw afterwards.
5. Choose an installed local model and click Apply changes. Defaults: qwen2.5:3b, 55 WPM, 3% optional typing corrections. The 3B model is retained for your personal testing; check its model license separately before commercial use/distribution.

For troubleshooting, open PowerShell inside this folder and run `py app.py` (keeps console visible). If `tkinter` is missing, use a Python installation that includes Tcl/Tk. Existing CLI remains available with `py ghosttype.py --model qwen2.5:3b` (do not run both at once).

## Controls

- Ctrl+Shift+Space: replace selected instruction with complete response.
- Ctrl+Shift+F9: paced character-by-character output; single-line printable text only.
- Esc: stop paced typing. Partial text may remain; review or undo in target editor.
- Cancel task (window or tray menu): prevents insertion once pending generation returns; does not interrupt the HTTP request itself.
- Pause: disables processing of shortcuts (registered combinations remain reserved).
- Apply changes: registers both shortcuts and persists preferences in `%LOCALAPPDATA%\GhostType\settings.json`. Shortcut modifier is Ctrl+Shift, selectable key Space or F6–F12. Conflicting hotkeys are reported.
- Close window: hides it if tray preference is enabled and tray registration succeeded. Double-click tray icon to restore; right-click for Open, Pause, Cancel, Exit. The icon is a standard Windows application icon in this beta.
- Startup: opt-in per-user Windows Run registry entry, pointing at the current pythonw and app.py. Turn it off before moving/deleting the folder. No admin privileges required.
- Refresh: checks Ollama and lists installed local models. Status is a connectivity snapshot, not continuous monitoring.

## Safety and limits

Use Notepad first, not important documents, password fields, terminals, or forms that submit automatically. The engine rechecks selected text and focus before insertion, but race conditions remain. Paced mode checks focus and cancellation repeatedly; editing within the same control can still interfere. The clipboard is used internally with best-effort plain-text restoration; rich formatting and clipboard history are not preserved. Never assume output is human-authored. AI text may contain errors. No prompt or answer logs are saved by GhostType. The app uses local Ollama HTTP only (cloud-named models filtered), but users should separately check Ollama/model configuration. No universal undo, live token streaming, installer, or binary signing yet.

## Verification

Run `py -m unittest discover -v`. Tests cover mocked HTTP, typing event generation, and settings validation/persistence. Desktop integration (Win32 hotkeys, tray, registry, GUI, real clipboard) requires live Windows testing. No Windows execution or graphical rendering was performed in the build environment.

Source code: MIT license (see LICENSE). Model and dependency licenses are separate. This is a private beta, not a production-ready release.
