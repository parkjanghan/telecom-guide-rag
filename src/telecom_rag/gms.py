"""Small SSAFY GMS Responses client; no credentials or raw error-body logging."""
from dataclasses import dataclass
import json
from typing import Any
import httpx
from .settings import GMSSettings


class GMSClientError(RuntimeError):
    def __init__(self, code: str, status_code: int | None = None):
        self.code = code
        self.status_code = status_code
        suffix = f' (HTTP {status_code})' if status_code is not None else ''
        super().__init__('GMS request failed: ' + code + suffix)


@dataclass(frozen=True)
class GMSResponse:
    text: str
    model: str
    status: str
    usage: dict[str, int]


def parse_response(data: Any) -> GMSResponse:
    if not isinstance(data, dict):
        raise GMSClientError('invalid_response')
    status = data.get('status')
    if status != 'completed':
        raise GMSClientError('response_incomplete' if status == 'incomplete' else 'response_not_completed')
    parts = []
    for item in data.get('output', []):
        if not isinstance(item, dict) or item.get('type') != 'message' or item.get('role') != 'assistant':
            continue
        for part in item.get('content', []):
            if not isinstance(part, dict):
                continue
            if part.get('type') == 'refusal':
                raise GMSClientError('model_refused')
            if part.get('type') == 'output_text' and isinstance(part.get('text'), str):
                parts.append(part['text'])
    text = '\n'.join(parts).strip()
    if not text:
        raise GMSClientError('empty_output')
    raw_usage = data.get('usage') or {}
    usage = {key: raw_usage[key] for key in ['input_tokens','output_tokens','total_tokens']
             if isinstance(raw_usage, dict) and type(raw_usage.get(key)) is int}
    return GMSResponse(text=text, model=str(data.get('model', '')), status=status, usage=usage)


class GMSClient:
    def __init__(self, settings: GMSSettings, transport: httpx.BaseTransport | None = None):
        self.settings = settings
        self.transport = transport

    def respond(self, text: str, *, instructions: str | None = None,
                max_output_tokens: int = 512) -> GMSResponse:
        if not self.settings.status()['ready']:
            raise GMSClientError('settings_not_ready')
        if not text.strip() or not 1 <= max_output_tokens <= 8192:
            raise ValueError('Require non-empty input and max_output_tokens in 1..8192')
        payload = {'model': self.settings.model, 'input': text,
                   'max_output_tokens': max_output_tokens, 'store': False}
        if instructions:
            payload['instructions'] = instructions
        # No redirects (including to a different host), and no automatic retries.
        try:
            with httpx.Client(timeout=self.settings.timeout_seconds,
                              follow_redirects=False, transport=self.transport) as client:
                response = client.post(self.settings.api_url,
                    headers={'Authorization':'Bearer ' + self.settings.api_key,
                             'Content-Type':'application/json'}, json=payload)
        except httpx.TimeoutException:
            raise GMSClientError('timeout') from None
        except httpx.RequestError:
            raise GMSClientError('network_error') from None
        if not 200 <= response.status_code < 300:
            raise GMSClientError('http_error', response.status_code) from None
        try:
            data = response.json()
        except (ValueError, UnicodeError):
            raise GMSClientError('invalid_json') from None
        return parse_response(data)
