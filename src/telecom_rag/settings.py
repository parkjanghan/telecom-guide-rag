"""Load local GMS configuration without logging or exposing API keys."""
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse
import os
from dotenv import dotenv_values

@dataclass(frozen=True)
class GMSSettings:
    api_key: str = field(repr=False)
    api_url: str
    model: str
    timeout_seconds: int

    @classmethod
    def load(cls, repo: Path):
        values = dotenv_values(repo/'.env', encoding='utf-8-sig')
        def value(key, default=''):
            return os.environ.get(key) or values.get(key) or default
        return cls(value('GMS_KEY'), value('GMS_API_URL'), value('GMS_MODEL'),
                   int(value('GMS_TIMEOUT_SECONDS','60')))

    def status(self):
        parsed=urlparse(self.api_url)
        # Do not echo URL credentials/query strings or the API key.
        valid=(parsed.scheme=='https' and parsed.hostname=='gms.ssafy.io'
               and parsed.path.endswith('/responses') and not parsed.username
               and not parsed.password and not parsed.query and not parsed.fragment)
        return {'provider':'SSAFY GMS', 'key_configured':bool(self.api_key.strip()),
                'endpoint_valid':valid, 'model':self.model,
                'timeout_seconds':self.timeout_seconds,
                'ready':bool(self.api_key.strip()) and valid and bool(self.model)
                        and self.timeout_seconds>0,
                'network_request_sent':False}
