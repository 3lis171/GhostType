import random
import unittest
from typing_mode import typing_events

class TypingTests(unittest.TestCase):
    def test_roundtrip(self):
        text = 'Hallo, schöne Welt! ABC xyz 😊'
        events = list(typing_events(text, 55, 0.15, random.Random(4)))
        out = ''
        for action, char, delay in events:
            out = out[:-1] if action == 'backspace' else out + char
            self.assertGreater(delay, 0)
        self.assertEqual(out, text)
        self.assertTrue(any(e[0] == 'backspace' for e in events))
    def test_no_typos(self):
        self.assertEqual(''.join(e[1] for e in typing_events('abc def')), 'abc def')
    def test_multiline(self):
        with self.assertRaises(ValueError): list(typing_events('a\nb'))
    def test_limits(self):
        for wpm, rate in [(0, 0), (55, 1)]:
            with self.assertRaises(ValueError): list(typing_events('abc', wpm, rate))
