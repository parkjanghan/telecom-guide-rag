import unittest
from pathlib import Path
from unittest.mock import patch
from telecom_rag.settings import GMSSettings

class GMSSettingsTests(unittest.TestCase):
    def test_key_never_appears_in_repr_or_status(self):
        key='test-secret-value'
        settings=GMSSettings(key,'https://gms.ssafy.io/gmsapi/api.openai.com/v1/responses','gpt-6.1-sol',60)
        self.assertNotIn(key,repr(settings));self.assertNotIn(key,str(settings.status()))
        self.assertTrue(settings.status()['ready'])
    def test_empty_key_is_not_ready(self):
        s=GMSSettings('','https://gms.ssafy.io/gmsapi/api.openai.com/v1/responses','gpt-6.1-sol',60)
        self.assertFalse(s.status()['ready'])
        self.assertFalse(s.status()['network_request_sent'])
    def test_credentials_or_wrong_endpoint_rejected(self):
        for url in ['https://example.org/responses','https://secret@gms.ssafy.io/responses',
                    'https://gms.ssafy.io/responses?key=secret']:
            self.assertFalse(GMSSettings('key',url,'model',60).status()['ready'])
if __name__=='__main__':unittest.main()
