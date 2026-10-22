import copy,json,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from telecom_rag.semantic_plan import SemanticPlanner,SemanticPlanError,validate_plan,retrieval_queries
from telecom_rag.gms import GMSResponse

QUESTION='제 명의 휴대폰에서 명의는 유지하고 납부계좌만 변경하고 싶어요.'
def sample():
 return {'schema_version':'1.0','intents':[{'goal':'납부계좌 변경','search_query':'본인 명의 휴대폰 납부계좌 변경','services':['모바일'],'operators':['미확인'],'evidence_quotes':['납부계좌만 변경']}], 'facts':[{'key':'회선 명의자','value':'본인','quote':'제 명의 휴대폰'}],'constraints':[{'kind':'preserve','text':'명의 유지','quote':'명의는 유지'}],'unknowns':['사용 사업자']}

class SemanticPlanTests(unittest.TestCase):
 def test_quotes_must_come_from_question(self):
  value=sample();value['facts'][0]['quote']='부모님 명의'
  with self.assertRaisesRegex(SemanticPlanError,'ungrounded_quote'):validate_plan(value,QUESTION)
 def test_empty_intent_rejected(self):
  value=sample();value['intents']=[]
  with self.assertRaises(SemanticPlanError):validate_plan(value,QUESTION)
 def test_unknown_service_rejected(self):
  value=sample();value['intents'][0]['services']=['추측한 서비스']
  with self.assertRaises(SemanticPlanError):validate_plan(value,QUESTION)
 def test_unexpected_policy_field_rejected(self):
  value=sample();value['answer']='동의가 필요 없습니다'
  with self.assertRaises(SemanticPlanError):validate_plan(value,QUESTION)
 def test_whole_question_and_constraints_remain(self):
  value=validate_plan(sample(),QUESTION)
  self.assertEqual(retrieval_queries(QUESTION,value)[0]['text'],QUESTION)
  self.assertEqual(value['constraints'][0]['quote'],'명의는 유지')
 def test_successful_plan_is_cached_without_another_api_call(self):
  client=Mock();client.settings=SimpleNamespace(model='test-model',api_url='https://gms.ssafy.io/responses')
  client.respond.return_value=GMSResponse(json.dumps(sample(),ensure_ascii=False),'test-model','completed',{'total_tokens':10})
  with patch.object(Path,'read_text',return_value='prompt') as read, \
       patch.object(Path,'exists',side_effect=[False,True]), \
       patch.object(Path,'mkdir'),patch.object(Path,'write_text'):
   planner=SemanticPlanner(Path('repo'),client=client)
   first=planner.plan(QUESTION);read.return_value=json.dumps(first)
   second=planner.plan(QUESTION)
  self.assertEqual(client.respond.call_count,1)
  self.assertTrue(second['cache_hit']);self.assertFalse(second['network_request_sent'])
 def test_invalid_json_is_not_cached(self):
  client=Mock();client.settings=SimpleNamespace(model='test-model',api_url='https://gms.ssafy.io/responses')
  client.respond.return_value=GMSResponse('not-json','test-model','completed',{})
  with patch.object(Path,'read_text',return_value='prompt'),patch.object(Path,'exists',return_value=False),patch.object(Path,'write_text') as write:
   planner=SemanticPlanner(Path('repo'),client=client)
   with self.assertRaisesRegex(SemanticPlanError,'invalid_plan_json'):planner.plan(QUESTION)
   write.assert_not_called()
if __name__=='__main__':unittest.main()
