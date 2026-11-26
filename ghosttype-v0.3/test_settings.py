import unittest, tempfile
from pathlib import Path
from settings import load,save,validate,DEFAULTS
class SettingsTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'settings.json'; s={**DEFAULTS,'wpm':87,'startup':True}; save(s,p); self.assertEqual(load(p),s)
    def test_corrupt(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'settings.json'; p.write_text('{'); self.assertEqual(load(p),DEFAULTS)
    def test_conflict(self):
        with self.assertRaises(ValueError): validate({**DEFAULTS,'paced':'Space'})
    def test_bounds(self):
        for x in [{'wpm':9},{'typos':.16},{'model':'qwen:cloud'},{'tray':'yes'}]:
            with self.assertRaises(ValueError): validate({**DEFAULTS,**x})
