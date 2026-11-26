"""Local Ollama client; independent of Windows integration."""
import json
from urllib.request import Request, build_opener, ProxyHandler

DEFAULT_MODEL = 'qwen2.5:1.5b'
SYSTEM = ('You are an inline text assistant. Carry out the user instruction. '
          'If asked to rewrite or translate, return only the resulting text. '
          'If asked a question, return the answer directly. Do not add a preamble '
          'or wrap the output in quotes unless requested. You cannot execute actions.')

def generate(prompt, model=DEFAULT_MODEL, timeout=120):
    if not prompt.strip():
        raise ValueError('Select a non-empty instruction first.')
    if len(prompt) > 12000:
        raise ValueError('Selection too long (maximum 12,000 characters).')
    if ':cloud' in model.lower() or model.lower().endswith('-cloud'):
        raise ValueError('GhostType supports local models only.')
    request = Request('http://127.0.0.1:11434/api/generate',
                      data=json.dumps({'model': model, 'prompt': prompt,
                                       'system': SYSTEM, 'stream': False}).encode('utf-8'),
                      headers={'Content-Type': 'application/json'}, method='POST')
    # Never use a system HTTP proxy for requests containing selected text.
    with build_opener(ProxyHandler({})).open(request, timeout=timeout) as reply:
        data = json.load(reply)
    if data.get('error'):
        raise RuntimeError(data['error'])
    result = data.get('response', '').strip()
    if not result:
        raise RuntimeError('The model returned an empty response.')
    return result
