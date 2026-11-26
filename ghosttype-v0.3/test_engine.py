import io
import json
import unittest
from unittest.mock import patch
from engine import generate

class EngineTests(unittest.TestCase):
    @patch('engine.build_opener')
    def test_local_request(self, opener):
        opener.return_value.open.return_value = io.BytesIO(b'{"response":" Hello! "}')
        self.assertEqual(generate('Say hello'), 'Hello!')
        req = opener.return_value.open.call_args.args[0]
        self.assertEqual(req.full_url, 'http://127.0.0.1:11434/api/generate')
        self.assertEqual(json.loads(req.data)['prompt'], 'Say hello')
        self.assertFalse(json.loads(req.data)['stream'])
    def test_empty(self):
        with self.assertRaises(ValueError): generate(' ')
    def test_cloud(self):
        with self.assertRaises(ValueError): generate('Hi', 'example:cloud')
    def test_too_long(self):
        with self.assertRaises(ValueError): generate('x'*12001)
    @patch('engine.build_opener')
    def test_empty_response(self, opener):
        opener.return_value.open.return_value = io.BytesIO(b'{"response":" "}')
        with self.assertRaises(RuntimeError): generate('Hi')

if __name__ == '__main__': unittest.main()
