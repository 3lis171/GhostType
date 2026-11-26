"""GhostType desktop settings. Python 3 with Tk; Windows only."""
import sys, queue, threading, json
import tkinter as tk
from tkinter import ttk, messagebox
from urllib.request import build_opener, ProxyHandler
from settings import load, save, validate, startup, KEYS

BG='#202124'; PANEL='#282a2d'; FG='#e8eaed'; MUTED='#a9adb4'; ACCENT='#8ab4f8'; LINE='#3b3e43'

class App:
    def __init__(self, root):
        from native import Native
        self.root=root; self.s=load(); self.events=queue.Queue(); self.busy=False; self.paused=False; self.has_tray=False; self.pending=False; self.closing=False; self.engine_ok=False; self.hotkeys_ok=False
        root.title('GhostType'); root.geometry('700x735'); root.minsize(660,700); root.configure(bg=BG); root.protocol('WM_DELETE_WINDOW',self.close)
        root.option_add('*Font','{Segoe UI} 10'); root.option_add('*TCombobox*Listbox.background',PANEL); root.option_add('*TCombobox*Listbox.foreground',FG)
        style=ttk.Style(root); style.theme_use('clam'); style.configure('.',background=BG,foreground=FG,font=('Segoe UI',10)); style.configure('TFrame',background=BG); style.configure('TLabel',background=BG,foreground=FG); style.configure('Muted.TLabel',foreground=MUTED); style.configure('TButton',background=PANEL,foreground=FG,padding=(14,7),bordercolor=LINE,lightcolor=PANEL,darkcolor=PANEL); style.map('TButton',background=[('active','#393c42'),('pressed','#454950')],foreground=[('disabled','#777a80')]); style.configure('Accent.TButton',background='#b0c7ed',foreground='#152336'); style.map('Accent.TButton',background=[('active','#c9dafa'),('pressed','#91add9')]); style.configure('TCheckbutton',background=BG,foreground=FG); style.map('TCheckbutton',background=[('active',BG)],indicatorcolor=[('selected',ACCENT),('!selected',PANEL)]); style.configure('TCombobox',fieldbackground=PANEL,background=PANEL,foreground=FG,arrowcolor=FG,bordercolor=LINE,lightcolor=PANEL,darkcolor=PANEL); style.map('TCombobox',fieldbackground=[('readonly',PANEL)],foreground=[('readonly',FG)]); style.configure('Horizontal.TScale',background=BG,troughcolor=LINE); style.configure('TSeparator',background=LINE)
        self.v={k:(tk.BooleanVar(value=v) if isinstance(v,bool) else tk.DoubleVar(value=v) if isinstance(v,(int,float)) else tk.StringVar(value=v)) for k,v in self.s.items()}
        self.status=tk.StringVar(value='Starting keyboard shortcuts…'); self.conn=tk.StringVar(value='Checking Ollama…'); self.hot=tk.StringVar(value='Starting'); self.speed=tk.StringVar(); self.typo=tk.StringVar()
        self.build(); self.native=Native(self.s,self.events); self.refresh(); root.after(70,self.poll)
    def label(self,p,t,muted=False): return ttk.Label(p,text=t,style='Muted.TLabel' if muted else 'TLabel')
    def section(self,p,title):
        ttk.Separator(p).pack(fill='x',pady=(15,13)); tk.Label(p,text=title,bg=BG,fg=FG,font=('Segoe UI Semibold',11)).pack(anchor='w',pady=(0,8))
    def row(self,p,title,description=None):
        r=ttk.Frame(p); r.pack(fill='x',pady=5); left=ttk.Frame(r); left.pack(side='left',fill='x',expand=True); self.label(left,title).pack(anchor='w');
        if description: self.label(left,description,True).pack(anchor='w',pady=(2,0))
        return r
    def build(self):
        head=ttk.Frame(self.root,padding=(28,20,28,12)); head.pack(fill='x'); tk.Label(head,text='GhostType',font=('Segoe UI Semibold',23),bg=BG,fg=FG).pack(side='left'); self.label(head,'0.3  /  Windows',True).pack(side='right',anchor='s',pady=6)
        body=ttk.Frame(self.root,padding=(28,0,28,0)); body.pack(fill='both',expand=True)
        top=ttk.Frame(body); top.pack(fill='x'); ttk.Label(top,textvariable=self.conn,style='Muted.TLabel').pack(side='left'); ttk.Label(top,textvariable=self.hot,style='Muted.TLabel').pack(side='right')
        self.section(body,'Local model'); r=self.row(body,'Ollama model','Installed models on this computer'); self.models=ttk.Combobox(r,textvariable=self.v['model'],values=[self.s['model']],state='readonly',width=23); self.models.pack(side='right',padx=(12,0)); ttk.Button(r,text='Refresh',command=self.refresh).pack(side='right')
        self.section(body,'Text output'); r=self.row(body,'Typing speed','Paced mode only'); ttk.Label(r,textvariable=self.speed,width=10).pack(side='right'); ttk.Scale(r,from_=10,to=200,variable=self.v['wpm'],command=self.update_labels,length=175).pack(side='right',padx=10)
        r=self.row(body,'Typing corrections','Optional simulated mistakes'); ttk.Label(r,textvariable=self.typo,width=10).pack(side='right'); ttk.Scale(r,from_=0,to=.15,variable=self.v['typos'],command=self.update_labels,length=175).pack(side='right',padx=10); self.update_labels()
        self.section(body,'Keyboard shortcuts')
        for k,title in [('instant','Insert response immediately'),('paced','Type response gradually')]:
            r=self.row(body,title); ttk.Combobox(r,textvariable=self.v[k],values=list(KEYS),state='readonly',width=9).pack(side='right'); self.label(r,'Ctrl + Shift +').pack(side='right',padx=8)
        self.label(body,'Esc stops paced typing. Review generated text before using it.',True).pack(anchor='w',pady=(3,0))
        self.section(body,'Application'); ttk.Checkbutton(body,text='Start GhostType when I sign in to Windows',variable=self.v['startup']).pack(anchor='w',pady=2); ttk.Checkbutton(body,text='Keep running in the notification area when closed',variable=self.v['tray']).pack(anchor='w',pady=2)
        footer=ttk.Frame(self.root,padding=(28,8,28,16)); footer.pack(fill='x',side='bottom'); ttk.Separator(footer).pack(fill='x',pady=(0,10)); r=ttk.Frame(footer); r.pack(fill='x'); self.pause_btn=ttk.Button(r,text='Pause',command=self.toggle); self.pause_btn.pack(side='left'); self.cancel_btn=ttk.Button(r,text='Cancel task',command=self.cancel,state='disabled'); self.cancel_btn.pack(side='left',padx=8); self.apply_btn=ttk.Button(r,text='Apply changes',style='Accent.TButton',command=self.apply); self.apply_btn.pack(side='right'); ttk.Label(footer,textvariable=self.status,style='Muted.TLabel',wraplength=620).pack(anchor='w',pady=(8,0))
    def update_labels(self,*_): self.speed.set(f'{round(self.v["wpm"].get())} WPM'); self.typo.set(f'{self.v["typos"].get()*100:.1f}%')
    def refresh(self):
        self.conn.set('Checking Ollama…')
        def work():
            try:
                with build_opener(ProxyHandler({})).open('http://127.0.0.1:11434/api/tags',timeout=4) as r: data=json.load(r)
                models=sorted({x['name'] for x in data.get('models',[]) if 'cloud' not in x['name'].lower()}); self.events.put(('models',models))
            except Exception: self.events.put(('models',None))
        threading.Thread(target=work,daemon=True).start()
    def apply(self):
        if self.pending or self.busy: return
        try:
            s=validate({k:(round(v.get()) if k=='wpm' else round(v.get(),3) if k=='typos' else v.get()) for k,v in self.v.items()}); self.pending=True; self.apply_btn.config(state='disabled'); self.native.command('settings',s)
        except Exception as e: messagebox.showerror('GhostType',str(e),parent=self.root)
    def toggle(self): self.native.command('pause',not self.paused)
    def cancel(self): self.native.cancel.set(); self.status.set('Cancellation requested — waiting for current task to finish.')
    def show(self): self.root.deiconify(); self.root.lift(); self.root.focus_force()
    def close(self):
        if self.s['tray'] and self.has_tray: self.root.withdraw()
        else: self.exit()
    def exit(self):
        if self.busy:
            self.closing=True; self.cancel(); self.show(); self.status.set('Stopping current task before exit…'); return
        self.native.stop(); self.root.after(150,self.root.destroy)
    def poll(self):
        while True:
            try: kind,val=self.events.get_nowait()
            except queue.Empty: break
            if kind=='status': self.status.set(val)
            elif kind=='fatal': self.status.set('Startup error: '+val); self.hot.set('Shortcuts unavailable'); self.show(); self.apply_btn.config(state='disabled')
            elif kind=='tray':
                self.has_tray=val
                if '--hidden' in sys.argv and val: self.root.withdraw()
            elif kind=='ready': self.hotkeys_ok=val; self.hot.set('Shortcuts active' if val else 'Shortcuts unavailable'); self.status.set('Ready. Select text in another application.' if val else 'Choose different shortcuts and apply.')
            elif kind=='show': self.show()
            elif kind=='exit': self.exit()
            elif kind=='paused': self.paused=val; self.pause_btn.config(text='Resume' if val else 'Pause'); self.hot.set('Paused' if val else 'Shortcuts active' if self.hotkeys_ok else 'Shortcuts unavailable')
            elif kind=='busy':
                self.busy=val; self.cancel_btn.config(state='normal' if val else 'disabled'); self.apply_btn.config(state='disabled' if val or self.pending else 'normal')
                if not val and self.closing: self.exit()
            elif kind=='models':
                self.engine_ok=val is not None; self.conn.set('Ollama connected' if self.engine_ok else 'Ollama unavailable — open Ollama and refresh')
                if val is not None:
                    self.models.config(values=val or [self.s['model']]);
                    if val and self.v['model'].get() not in val: self.v['model'].set(val[0])
            elif kind=='applied':
                self.pending=False; self.hotkeys_ok=True; self.hot.set('Paused' if self.paused else 'Shortcuts active'); self.s=val.copy()
                try: startup(val['startup']); save(val); self.status.set('Settings saved.')
                except Exception as e: self.status.set('Settings active, but could not save: '+str(e))
                self.apply_btn.config(state='normal' if not self.busy else 'disabled')
            elif kind=='apply_error': self.pending=False; self.apply_btn.config(state='normal'); self.status.set(val)
        self.root.after(70,self.poll)

def main():
    if sys.platform!='win32': raise SystemExit('GhostType desktop requires Windows.')
    root=tk.Tk(); App(root); root.mainloop()
if __name__=='__main__': main()
