"""Persistent per-user settings; no prompts or generated text are stored."""
import json, os, sys
from pathlib import Path
DEFAULTS = dict(model='qwen2.5:3b', wpm=55, typos=0.03, instant='Space', paced='F9', tray=True, startup=False)
KEYS = {'Space': 0x20, **{f'F{i}':0x6F+i for i in range(6,13)}}
PATH = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'GhostType' / 'settings.json'

def validate(data):
    s = {**DEFAULTS, **{k:v for k,v in data.items() if k in DEFAULTS}}
    if not isinstance(s['model'], str) or not s['model'].strip() or 'cloud' in s['model'].lower():
        raise ValueError('Choose an installed local model.')
    if not isinstance(s['wpm'], int) or not 10 <= s['wpm'] <= 200: raise ValueError('Speed must be 10–200 WPM.')
    if not isinstance(s['typos'], (float,int)) or not 0 <= s['typos'] <= .15: raise ValueError('Correction rate must be 0–15%.')
    if s['instant'] not in KEYS or s['paced'] not in KEYS or s['instant']==s['paced']: raise ValueError('Choose two distinct shortcuts.')
    if not all(isinstance(s[k],bool) for k in ('tray','startup')): raise ValueError('Invalid system preferences.')
    return s

def load(path=PATH):
    try: return validate(json.loads(path.read_text(encoding='utf8')))
    except (OSError,ValueError,TypeError,AttributeError): return DEFAULTS.copy()

def save(s,path=PATH):
    s=validate(s); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp'); tmp.write_text(json.dumps(s,indent=2),encoding='utf8'); tmp.replace(path)

def startup(enabled):
    import winreg, subprocess
    pythonw = Path(sys.executable).with_name('pythonw.exe')
    script = Path(__file__).resolve().with_name('app.py')
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
        if enabled:
            if not pythonw.is_file(): raise RuntimeError('pythonw.exe was not found; automatic startup not enabled.')
            winreg.SetValueEx(key,'GhostType',0,winreg.REG_SZ,subprocess.list2cmdline([str(pythonw),str(script),'--hidden']))
        else:
            try: winreg.DeleteValue(key,'GhostType')
            except FileNotFoundError: pass
