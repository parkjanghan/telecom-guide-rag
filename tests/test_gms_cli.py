import contextlib
import io
import unittest
from pathlib import Path
from unittest.mock import patch
from telecom_rag.__main__ import main
from telecom_rag.gms import GMSClientError
from telecom_rag.settings import GMSSettings

class GMSSmokeCLITests(unittest.TestCase):
    def test_failure_is_machine_readable_nonzero_and_does_not_expose_key(self):
        settings=GMSSettings('test-private-key','https://gms.ssafy.io/gmsapi/api.openai.com/v1/responses','gpt-6.1-sol',5)
        output=io.StringIO()
        with patch('sys.argv',['telecom_rag','gms-smoke']), \
             patch('telecom_rag.settings.GMSSettings.load',return_value=settings), \
             patch('telecom_rag.gms.GMSClient.respond',side_effect=GMSClientError('http_error',401)), \
             contextlib.redirect_stdout(output):
            with self.assertRaises(SystemExit) as error:main()
        self.assertEqual(error.exception.code,1)
        self.assertIn('http_error',output.getvalue())
        self.assertNotIn('test-private-key',output.getvalue())

if __name__=='__main__':unittest.main()
