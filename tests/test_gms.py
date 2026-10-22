import json
import unittest
import httpx
from telecom_rag.gms import GMSClient, GMSClientError, parse_response
from telecom_rag.settings import GMSSettings


def completed(text='GMS_CONNECTION_OK'):
    return {'status':'completed','model':'gpt-6.1-sol',
            'output':[{'type':'reasoning'}, {'type':'message','role':'assistant',
                       'content':[{'type':'output_text','text':text}]}],
            'usage':{'input_tokens':10,'output_tokens':5,'total_tokens':15}}


class GMSClientTests(unittest.TestCase):
    def settings(self, key='test-secret'):
        return GMSSettings(key,'https://gms.ssafy.io/gmsapi/api.openai.com/v1/responses','gpt-6.1-sol',5)

    def test_request_preserves_user_model_and_uses_responses_contract(self):
        requests=[]
        def handle(request):
            requests.append(request)
            self.assertEqual(request.headers['authorization'],'Bearer test-secret')
            body=json.loads(request.content)
            self.assertEqual(body['model'],'gpt-6.1-sol')
            self.assertFalse(body['store'])
            self.assertEqual(body['input'],'hello')
            return httpx.Response(200,json=completed())
        result=GMSClient(self.settings(),httpx.MockTransport(handle)).respond('hello')
        self.assertEqual(result.text,'GMS_CONNECTION_OK')
        self.assertEqual(result.usage['total_tokens'],15)
        self.assertEqual(len(requests),1)

    def test_incomplete_is_never_treated_as_answer(self):
        data=completed('partial text');data['status']='incomplete'
        with self.assertRaisesRegex(GMSClientError,'response_incomplete'):parse_response(data)

    def test_error_body_never_exposes_key_and_is_not_retried(self):
        calls=[]
        def handle(request):
            calls.append(request)
            return httpx.Response(401,text='sensitive test-secret content')
        with self.assertRaises(GMSClientError) as error:
            GMSClient(self.settings(),httpx.MockTransport(handle)).respond('hello')
        self.assertNotIn('test-secret',str(error.exception))
        self.assertEqual(error.exception.status_code,401)
        self.assertEqual(len(calls),1)

    def test_redirect_does_not_receive_credentials(self):
        calls=[]
        def handle(request):
            calls.append(request)
            return httpx.Response(307,headers={'Location':'https://example.org'})
        with self.assertRaises(GMSClientError):
            GMSClient(self.settings(),httpx.MockTransport(handle)).respond('hello')
        self.assertEqual(len(calls),1)

    def test_missing_key_sends_no_request(self):
        def fail(request):raise AssertionError('network must not be called')
        with self.assertRaisesRegex(GMSClientError,'settings_not_ready'):
            GMSClient(self.settings(''),httpx.MockTransport(fail)).respond('hello')

    def test_timeout_is_sanitized(self):
        def handle(request):raise httpx.ReadTimeout('test-secret',request=request)
        with self.assertRaises(GMSClientError) as error:
            GMSClient(self.settings(),httpx.MockTransport(handle)).respond('hello')
        self.assertEqual(error.exception.code,'timeout')
        self.assertNotIn('test-secret',str(error.exception))

    def test_empty_output_rejected(self):
        with self.assertRaisesRegex(GMSClientError,'empty_output'):parse_response(completed(' '))

    def test_refusal_rejected(self):
        data=completed();data['output'][1]['content']=[{'type':'refusal','refusal':'no'}]
        with self.assertRaisesRegex(GMSClientError,'model_refused'):parse_response(data)

    def test_invalid_json_is_safe(self):
        transport=httpx.MockTransport(lambda request:httpx.Response(200,text='test-secret'))
        with self.assertRaisesRegex(GMSClientError,'invalid_json'):
            GMSClient(self.settings(),transport).respond('hello')

if __name__=='__main__':unittest.main()
