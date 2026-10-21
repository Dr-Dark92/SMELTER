"""Bounded local model transport, independent of task orchestration/persistence."""
import json
import time
from urllib.request import Request
from urllib.error import HTTPError,URLError
from python_tools import MAX_CALLS
ENDPOINT='http://127.0.0.1:11434/api/chat'
MAX_RESPONSE=128*1024

class OllamaTurn:
    def __init__(self,model,messages,session,settings,opener,control):
        self.model,self.messages,self.session,self.settings,self.opener,self.control=model,messages,session,settings,opener,control
        self.deadline=time.monotonic()+settings['timeout_seconds']
    def checkpoint(self,phase=None):
        if self.control:self.control.update(phase) if phase else self.control.check()

    def infer(self, thinking, available_tools=None):
        self.checkpoint('Waiting for model')
        batch_limit = self.session.call_limit - len(self.session.events) if available_tools else MAX_CALLS
        request_messages = [dict(message) for message in self.messages]
        if not thinking:
            request_messages[0]['content'] += ' Respond directly and concisely.'
        from context_budget import bounded
        request_messages, budget = bounded(request_messages, available_tools, self.settings['context_tokens'], self.settings['max_output_tokens'])
        if self.control:
            self.control.context_budget = budget
        body = {'model': self.model, 'messages': request_messages, 'stream': False, 'think': thinking, 'options': {'num_predict': self.settings['max_output_tokens'], 'num_ctx': self.settings['context_tokens']}}
        if available_tools:
            body['tools'] = available_tools
        payload = json.dumps(body).encode()
        request = Request(ENDPOINT, data=payload, method='POST', headers={'Content-Type': 'application/json'})
        try:
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise ValueError('Chat turn time limit reached')
            if self.control:
                self.control.tool_call_limit = batch_limit
                raw = self.control.infer(body, max(1, remaining), 2 * 1024 * 1024)
            else:
                with self.opener(request, timeout=max(1, remaining)) as response:
                    raw = response.read(MAX_RESPONSE + 1)
            self.checkpoint()
        except (URLError, HTTPError, TimeoutError, OSError) as exc:
            raise ValueError('Local Ollama unavailable: ' + type(exc).__name__) from exc
        if len(raw) > MAX_RESPONSE:
            raise ValueError('Model response too large')
        try:
            result = json.loads(raw)
            message = result['message']
            if not isinstance(message, dict):
                raise ValueError('Invalid Ollama message')
            answer = message.get('content', '')
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ValueError('Invalid Ollama response') from exc
        if not isinstance(answer, str):
            raise ValueError('Invalid Ollama response content')
        calls = message.get('tool_calls', [])
        if not isinstance(calls, list) or len(calls) > batch_limit:
            raise ValueError('Invalid or excessive Ollama tool calls')
        return (answer, result.get('done_reason', 'unknown'), calls, message)
