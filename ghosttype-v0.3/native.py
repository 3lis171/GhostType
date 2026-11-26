"""Win32 hotkeys and notification area. Runs on a dedicated message thread."""
import ctypes as C
from ctypes import wintypes as W
import threading, queue, sys
from settings import KEYS
from ghosttype import Windows, MOD_CONTROL, MOD_SHIFT, MOD_NOREPEAT

class Native:
    def __init__(self, settings, events):
        self.settings=settings.copy(); self.events=events; self.commands=queue.Queue(); self.ready=threading.Event(); self.cancel=threading.Event(); self.busy=threading.Lock(); self.hwnd=None; self.registered=[]; self.paused=False; self.failure=None
        self.thread=threading.Thread(target=self.run,daemon=True); self.thread.start()
    def emit(self, kind, value=None): self.events.put((kind,value))
    def command(self,kind,value=None):
        self.commands.put((kind,value))
        if self.hwnd: self.u.PostMessageW(self.hwnd,0x8002,0,0)
    def stop(self): self.cancel.set(); self.command('quit')
    def register(self,s):
        for i in self.registered: self.u.UnregisterHotKey(self.hwnd,i)
        self.registered=[]
        for i,key in enumerate((s['instant'],s['paced']),1):
            if not self.u.RegisterHotKey(self.hwnd,i,MOD_CONTROL|MOD_SHIFT|MOD_NOREPEAT,KEYS[key]):
                for j in self.registered: self.u.UnregisterHotKey(self.hwnd,j)
                self.registered=[]; raise RuntimeError(f'Ctrl+Shift+{key} is unavailable. Another program may be using it.')
            self.registered.append(i)
    def trigger(self,i):
        if self.paused or not self.busy.acquire(False): return
        self.cancel.clear(); s=self.settings.copy()
        try:
            focus=self.backend.focus()
            if not focus[0]: raise RuntimeError('No active target window.')
            self.backend.extra_keys=(KEYS[s['instant']],KEYS[s['paced']])
            def work():
                try: self.backend.run_task(s['model'],focus,i==2,s['wpm'],s['typos'])
                finally: self.busy.release(); self.emit('busy',False)
            self.emit('busy',True); threading.Thread(target=work,daemon=True).start()
        except Exception as e: self.busy.release(); self.emit('status',str(e))
    def process(self):
        while True:
            try: kind,value=self.commands.get_nowait()
            except queue.Empty: return
            if kind=='quit': self.u.DestroyWindow(self.hwnd); return
            if kind=='pause':
                self.paused=value; self.cancel.set(); self.emit('paused',value)
            if kind=='settings':
                if self.busy.locked():
                    self.emit('apply_error','Wait for the current task to finish.'); continue
                old=self.settings
                try:
                    self.register(value); self.settings=value.copy(); self.emit('applied',value)
                except Exception as e:
                    try: self.register(old)
                    except Exception as restore: self.emit('status',str(restore))
                    self.emit('apply_error',str(e))
    def run(self):
        try: self._run()
        except Exception as e: self.failure=str(e); self.emit('fatal',str(e)); self.ready.set()
    def _run(self):
        self.backend=Windows(lambda s:self.emit('status',s),self.cancel)
        u=self.u=self.backend.u; k=C.WinDLL('kernel32',use_last_error=True); sh=C.WinDLL('shell32',use_last_error=True)
        LRESULT=C.c_ssize_t; WPARAM=C.c_size_t; LPARAM=C.c_ssize_t
        PROC=C.WINFUNCTYPE(LRESULT,W.HWND,W.UINT,WPARAM,LPARAM)
        class WC(C.Structure):
            _fields_=[('style',W.UINT),('lpfnWndProc',PROC),('cbClsExtra',C.c_int),('cbWndExtra',C.c_int),('hInstance',W.HINSTANCE),('hIcon',W.HICON),('hCursor',W.HANDLE),('hbrBackground',W.HBRUSH),('lpszMenuName',W.LPCWSTR),('lpszClassName',W.LPCWSTR)]
        class NID(C.Structure):
            _fields_=[('cbSize',W.DWORD),('hWnd',W.HWND),('uID',W.UINT),('uFlags',W.UINT),('uCallbackMessage',W.UINT),('hIcon',W.HICON),('szTip',W.WCHAR*128),('dwState',W.DWORD),('dwStateMask',W.DWORD),('szInfo',W.WCHAR*256),('uTimeout',W.UINT),('szInfoTitle',W.WCHAR*64),('dwInfoFlags',W.DWORD),('guidItem',C.c_byte*16),('hBalloonIcon',W.HICON)]
        def sig(dll,name,args,rest):
            f=getattr(dll,name); f.argtypes=args; f.restype=rest; return f
        sig(k,'GetModuleHandleW',[W.LPCWSTR],W.HINSTANCE)
        sig(u,'DefWindowProcW',[W.HWND,W.UINT,WPARAM,LPARAM],LRESULT)
        sig(u,'RegisterClassW',[C.POINTER(WC)],W.ATOM)
        sig(u,'CreateWindowExW',[W.DWORD,W.LPCWSTR,W.LPCWSTR,W.DWORD,C.c_int,C.c_int,C.c_int,C.c_int,W.HWND,W.HMENU,W.HINSTANCE,C.c_void_p],W.HWND)
        sig(u,'LoadIconW',[W.HINSTANCE,C.c_void_p],W.HICON)
        sig(u,'PostMessageW',[W.HWND,W.UINT,WPARAM,LPARAM],W.BOOL)
        sig(u,'DestroyWindow',[W.HWND],W.BOOL)
        sig(u,'DispatchMessageW',[C.POINTER(W.MSG)],LRESULT)
        sig(u,'TranslateMessage',[C.POINTER(W.MSG)],W.BOOL)
        sig(u,'CreatePopupMenu',[],W.HMENU)
        sig(u,'AppendMenuW',[W.HMENU,W.UINT,WPARAM,W.LPCWSTR],W.BOOL)
        sig(u,'TrackPopupMenu',[W.HMENU,W.UINT,C.c_int,C.c_int,C.c_int,W.HWND,C.c_void_p],W.BOOL)
        sig(u,'DestroyMenu',[W.HMENU],W.BOOL)
        sig(u,'GetCursorPos',[C.POINTER(W.POINT)],W.BOOL)
        sig(u,'SetForegroundWindow',[W.HWND],W.BOOL)
        sig(u,'RegisterWindowMessageW',[W.LPCWSTR],W.UINT)
        sig(sh,'Shell_NotifyIconW',[W.DWORD,C.POINTER(NID)],W.BOOL)
        taskbar=u.RegisterWindowMessageW('TaskbarCreated')
        nid=NID(); nid.cbSize=C.sizeof(nid); nid.uID=1; nid.uFlags=7; nid.uCallbackMessage=0x8001; nid.hIcon=u.LoadIconW(None,C.c_void_p(32512)); nid.szTip='GhostType — local AI'
        def menu(hwnd):
            m=u.CreatePopupMenu(); pt=W.POINT(); u.GetCursorPos(C.byref(pt))
            try:
                for id,label in [(1,'Open GhostType'),(2,'Resume shortcuts' if self.paused else 'Pause shortcuts'),(3,'Cancel current task'),(4,'Exit')]: u.AppendMenuW(m,0,id,label)
                u.SetForegroundWindow(hwnd)
                choice=u.TrackPopupMenu(m,0x102,pt.x,pt.y,0,hwnd,None)
                if choice==1: self.emit('show')
                elif choice==2: self.paused=not self.paused; self.cancel.set(); self.emit('paused',self.paused)
                elif choice==3: self.cancel.set(); self.emit('status','Cancellation requested.')
                elif choice==4: self.emit('exit')
                u.PostMessageW(hwnd,0,0,0)
            finally: u.DestroyMenu(m)
        @PROC
        def wnd(hwnd,msg,wp,lp):
            try:
                if msg==0x0312: self.trigger(int(wp)); return 0
                if msg==0x8002: self.process(); return 0
                if msg==0x8001:
                    if lp==0x205: menu(hwnd)
                    elif lp==0x203: self.emit('show')
                    return 0
                if msg==taskbar: sh.Shell_NotifyIconW(0,C.byref(nid)); return 0
                if msg==2:
                    sh.Shell_NotifyIconW(2,C.byref(nid)); u.PostQuitMessage(0); return 0
            except Exception as e: self.emit('status',str(e))
            return u.DefWindowProcW(hwnd,msg,wp,lp)
        instance=k.GetModuleHandleW(None); wc=WC(); wc.lpfnWndProc=wnd; wc.hInstance=instance; wc.lpszClassName='GhostTypeNative03'
        if not u.RegisterClassW(C.byref(wc)): raise C.WinError(C.get_last_error())
        self.hwnd=u.CreateWindowExW(0,wc.lpszClassName,'GhostType',0,0,0,0,0,None,None,instance,None)
        if not self.hwnd: raise C.WinError(C.get_last_error())
        nid.hWnd=self.hwnd
        tray=bool(sh.Shell_NotifyIconW(0,C.byref(nid))); self.emit('tray',tray)
        try:
            self.register(self.settings)
        except Exception as e: self.emit('status',str(e))
        self.ready.set(); self.emit('ready',bool(self.registered))
        msg=W.MSG()
        try:
            while True:
                r=u.GetMessageW(C.byref(msg),None,0,0)
                if r<=0: break
                u.TranslateMessage(C.byref(msg)); u.DispatchMessageW(C.byref(msg))
        finally:
            for i in self.registered: u.UnregisterHotKey(self.hwnd,i)
            sh.Shell_NotifyIconW(2,C.byref(nid)); self.hwnd=None
