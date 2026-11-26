"""GhostType v0.3: Windows-first, explicit hotkey, local AI."""
import argparse
import ctypes
from ctypes import wintypes
import sys
import time
import threading
from contextlib import suppress
from engine import generate, DEFAULT_MODEL
from typing_mode import typing_events

HOTKEY_ID = 1
HUMAN_HOTKEY_ID = 2
VK_F9, VK_ESCAPE, VK_BACK = 0x78, 0x1B, 0x08
KEYEVENTF_UNICODE = 4
WM_HOTKEY = 0x0312
MOD_CONTROL, MOD_SHIFT, MOD_NOREPEAT = 2, 4, 0x4000
VK_CONTROL, VK_SHIFT, VK_SPACE, VK_MENU = 0x11, 0x10, 0x20, 0x12
CF_UNICODETEXT = 13
KEYEVENTF_KEYUP = 2

class GUIThreadInfo(ctypes.Structure):
    _fields_ = [('cbSize', wintypes.DWORD), ('flags', wintypes.DWORD),
                ('hwndActive', wintypes.HWND), ('hwndFocus', wintypes.HWND),
                ('hwndCapture', wintypes.HWND), ('hwndMenuOwner', wintypes.HWND),
                ('hwndMoveSize', wintypes.HWND), ('hwndCaret', wintypes.HWND),
                ('rcCaret', wintypes.RECT)]

class KeyboardInput(ctypes.Structure):
    _fields_ = [('wVk', wintypes.WORD), ('wScan', wintypes.WORD),
                ('dwFlags', wintypes.DWORD), ('time', wintypes.DWORD),
                ('dwExtraInfo', ctypes.c_size_t)]

class MouseInput(ctypes.Structure):
    _fields_ = [('dx', wintypes.LONG), ('dy', wintypes.LONG),
                ('mouseData', wintypes.DWORD), ('dwFlags', wintypes.DWORD),
                ('time', wintypes.DWORD), ('dwExtraInfo', ctypes.c_size_t)]

class HardwareInput(ctypes.Structure):
    _fields_ = [('uMsg', wintypes.DWORD), ('wParamL', wintypes.WORD), ('wParamH', wintypes.WORD)]

class InputUnion(ctypes.Union):
    _fields_ = [('ki', KeyboardInput), ('mi', MouseInput), ('hi', HardwareInput)]

class Input(ctypes.Structure):
    _fields_ = [('type', wintypes.DWORD), ('data', InputUnion)]

class Windows:
    def __init__(self, report=None, cancel=None):
        import pyperclip
        self.clip = pyperclip
        self.report = report or (lambda message: print(message, flush=True))
        self.cancel = cancel or threading.Event()
        self.extra_keys = ()
        self.u = ctypes.WinDLL('user32', use_last_error=True)
        self.u.GetForegroundWindow.restype = wintypes.HWND
        self.u.GetGUIThreadInfo.argtypes = [wintypes.DWORD, ctypes.POINTER(GUIThreadInfo)]
        self.u.GetGUIThreadInfo.restype = wintypes.BOOL
        self.u.GetClipboardSequenceNumber.restype = wintypes.DWORD
        self.u.GetAsyncKeyState.argtypes = [ctypes.c_int]
        self.u.GetAsyncKeyState.restype = ctypes.c_short
        self.u.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
        self.u.GetMessageW.restype = ctypes.c_int
        self.u.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        self.u.RegisterHotKey.restype = wintypes.BOOL
        self.u.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        self.u.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
        self.u.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int]
        self.u.SendInput.restype = wintypes.UINT
        self.u.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_size_t]

    def focus(self):
        info = GUIThreadInfo()
        info.cbSize = ctypes.sizeof(info)
        if not self.u.GetGUIThreadInfo(0, ctypes.byref(info)):
            raise RuntimeError('Could not identify the focused window.')
        return (self.u.GetForegroundWindow(), info.hwndFocus)

    def seq(self):
        return self.u.GetClipboardSequenceNumber()

    def wait_keys(self):
        until = time.monotonic() + 3
        while any(self.u.GetAsyncKeyState(k) & 0x8000 for k in (VK_CONTROL, VK_SHIFT, VK_SPACE, VK_MENU, VK_F9, *self.extra_keys)):
            if time.monotonic() > until:
                raise RuntimeError('Release the shortcut keys and try again.')
            time.sleep(0.02)

    def chord(self, key):
        self.u.keybd_event(VK_CONTROL, 0, 0, 0)
        try:
            self.u.keybd_event(ord(key), 0, 0, 0)
            self.u.keybd_event(ord(key), 0, KEYEVENTF_KEYUP, 0)
        finally:
            self.u.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

    def copy_selection(self, focus, expected_seq):
        self.wait_keys()
        if self.focus() != focus or self.seq() != expected_seq:
            raise RuntimeError('Focus or clipboard changed; cancelled.')
        self.chord('C')
        until = time.monotonic() + 1.5
        while self.seq() == expected_seq:
            if time.monotonic() > until:
                raise RuntimeError('No copied selection. Highlight an instruction first.')
            time.sleep(0.02)
        # Give applications a moment to publish their clipboard formats.
        time.sleep(0.10)
        captured_seq = self.seq()
        return self.clip.paste(), captured_seq

    def check_cancel(self):
        if self.cancel.is_set():
            raise RuntimeError("Cancelled. Partial text may remain if typing had started.")

    def check_typing(self, focus):
        self.check_cancel()
        if self.focus() != focus:
            raise RuntimeError('Focus changed; typing stopped. Partial text may remain.')
        if any(self.u.GetAsyncKeyState(k) & 0x8000 for k in
               (VK_ESCAPE, VK_CONTROL, VK_SHIFT, VK_MENU, 0x5B, 0x5C, 1, 2, 4)):
            raise RuntimeError('Typing stopped by user input. Partial text may remain.')

    def send_keys(self, units, unicode=True):
        events = []
        for unit in units:
            for up in (0, KEYEVENTF_KEYUP):
                event = Input()
                event.type = 1  # INPUT_KEYBOARD
                event.data.ki = KeyboardInput(0 if unicode else unit,
                                              unit if unicode else 0,
                                              (KEYEVENTF_UNICODE if unicode else 0) | up, 0, 0)
                events.append(event)
        array = (Input * len(events))(*events)
        if self.u.SendInput(len(events), array, ctypes.sizeof(Input)) != len(events):
            raise RuntimeError('Windows rejected keyboard input; typing stopped.')

    def type_answer(self, answer, focus, wpm, typo_rate):
        # Validate the entire answer before modifying the selected text.
        if any(not ch.isprintable() for ch in answer):
            raise RuntimeError('Human mode supports single-line printable text only. Use Ctrl+Shift+Space for multiline output.')
        self.report('Typing — press Esc or switch windows to stop.')
        for action, text, delay in typing_events(answer, wpm, typo_rate):
            self.check_typing(focus)
            if action == 'backspace':
                self.send_keys([VK_BACK], unicode=False)
            else:
                raw = text.encode('utf-16-le')
                self.send_keys([int.from_bytes(raw[i:i+2], 'little') for i in range(0, len(raw), 2)])
            until = time.monotonic() + delay
            while time.monotonic() < until:
                self.check_typing(focus)
                time.sleep(min(0.015, max(0, until - time.monotonic())))
        self.report('Typing complete. Review the result.')

    def run_task(self, model, initial_focus, human=False, wpm=55, typo_rate=0):
        original = None
        owned_seq = None
        try:
            self.check_cancel()
            self.wait_keys()
            if self.focus() != initial_focus:
                raise RuntimeError('Focus changed; cancelled.')
            # Do not knowingly replace an image/file-only clipboard.
            if self.u.CountClipboardFormats() and not self.u.IsClipboardFormatAvailable(CF_UNICODETEXT):
                raise RuntimeError('Clipboard contains non-text data. Copy plain text first.')
            initial_seq = self.seq()
            original = self.clip.paste()
            if self.seq() != initial_seq:
                raise RuntimeError('Clipboard changed; try again.')
            prompt, owned_seq = self.copy_selection(initial_focus, initial_seq)
            if not prompt.strip():
                raise RuntimeError('Highlight a non-empty instruction first.')
            # Restore the user's text while the model works.
            if self.seq() != owned_seq:
                raise RuntimeError('Clipboard changed; cancelled.')
            self.clip.copy(original)
            owned_seq = self.seq()
            self.report('Generating locally — keep the selection highlighted.')
            answer = generate(prompt, model)
            self.check_cancel()
            self.wait_keys()
            if self.focus() != initial_focus or self.seq() != owned_seq:
                raise RuntimeError('Focus or clipboard changed while generating; cancelled.')
            # Re-read selected text to avoid overwriting a changed selection.
            selection, owned_seq = self.copy_selection(initial_focus, owned_seq)
            if selection != prompt or self.focus() != initial_focus:
                raise RuntimeError('Selection changed; cancelled.')
            if self.seq() != owned_seq:
                raise RuntimeError('Clipboard changed; cancelled.')
            self.check_cancel()
            if human:
                # Restore plain text before the long typing operation; do not touch it again.
                self.clip.copy(original)
                owned_seq = None
                self.type_answer(answer, initial_focus, wpm, typo_rate)
                return
            self.clip.copy(answer)
            owned_seq = self.seq()
            if self.focus() != initial_focus or self.seq() != owned_seq:
                raise RuntimeError('Focus or clipboard changed; cancelled.')
            self.check_cancel()
            self.chord('V')
            time.sleep(0.75)
            self.report('Paste requested. Review the result; Ctrl+Z may undo it.')
        except Exception as exc:
            self.report(f'Error: {exc}')
        finally:
            # Do not overwrite clipboard changes made by the user during generation.
            if original is not None and owned_seq is not None:
                try:
                    if self.seq() == owned_seq:
                        self.clip.copy(original)
                except Exception as exc:
                    self.report(f'Could not restore clipboard text: {exc}')

    def listen(self, model, wpm=55, typo_rate=0):
        lock = threading.Lock()
        def work(focus, human):
            try:
                self.run_task(model, focus, human, wpm, typo_rate)
            finally:
                lock.release()
        if not self.u.RegisterHotKey(None, HOTKEY_ID, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, VK_SPACE):
            raise ctypes.WinError(ctypes.get_last_error())
        if not self.u.RegisterHotKey(None, HUMAN_HOTKEY_ID, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, VK_F9):
            error = ctypes.get_last_error()
            self.u.UnregisterHotKey(None, HOTKEY_ID)
            raise ctypes.WinError(error)
        print(f'GhostType v0.3 | {model} | Ctrl+Shift+Space: paste | Ctrl+Shift+F9: type ({wpm} WPM) | Esc: stop typing', flush=True)
        try:
            msg = wintypes.MSG()
            while True:
                status = self.u.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if status == -1:
                    raise ctypes.WinError(ctypes.get_last_error())
                if status == 0:
                    break
                if msg.message == WM_HOTKEY and msg.wParam in (HOTKEY_ID, HUMAN_HOTKEY_ID):
                    if not lock.acquire(blocking=False):
                        print('Already generating.', flush=True)
                        continue
                    try:
                        focus = self.focus()
                        threading.Thread(target=work, args=(focus, msg.wParam == HUMAN_HOTKEY_ID), daemon=True).start()
                    except Exception as exc:
                        lock.release()
                        self.report(f'Error: {exc}')
        finally:
            self.u.UnregisterHotKey(None, HUMAN_HOTKEY_ID)
            self.u.UnregisterHotKey(None, HOTKEY_ID)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', default=DEFAULT_MODEL)
    parser.add_argument('--test', metavar='PROMPT', help='Test local AI without a global shortcut.')
    parser.add_argument('--wpm', type=int, default=55, help='Human typing speed (10–200 WPM).')
    parser.add_argument('--typos', type=float, default=0.0, help='Optional typo probability per ASCII letter (0–0.15).')
    args = parser.parse_args()
    if not 10 <= args.wpm <= 200 or not 0 <= args.typos <= 0.15:
        parser.error('Use --wpm 10–200 and --typos 0–0.15.')
    if args.test is not None:
        print(generate(args.test, args.model))
    elif sys.platform != 'win32':
        parser.error('Global shortcut mode currently requires Windows. --test works on other platforms.')
    else:
        Windows().listen(args.model, args.wpm, args.typos)

if __name__ == '__main__':
    main()
