import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from telecom_rag.availability import is_service_topic,TopicUnavailableError
from telecom_rag.chatbot import Chatbot
from telecom_rag.core import load_data
from telecom_rag.gms import GMSResponse

REPO=Path(__file__).resolve().parents[1]

class RecordingClient:
 def __init__(self,selected):self.selected=selected;self.calls=[]
 def respond(self,text,**kwargs):
  self.calls.append(json.loads(text))
  return GMSResponse(json.dumps({'selected_ids':self.selected,'reason':'test'}),'test','completed',{})

def make_bot(selected=None):
 store=SimpleNamespace(repo=REPO,topics={
  'supported':{'name':'일반 상담','summary':'근거 있는 상담','evidence_status':'linked_draft'},
  'draft':{'name':'준비 중 상담','summary':'조사용 초안','evidence_status':'missing','service_status':'unsupported_draft','support_reason':'대표 근거 준비 중'}})
 store.search_topics=lambda *a,**kw:[{'item_id':'draft'},{'item_id':'supported'}]
 store.engine=SimpleNamespace(tokenizer=SimpleNamespace(encode=lambda text,**kw:SimpleNamespace(offsets=[(i,i+1) for i in range(len(text))])))
 client=RecordingClient(selected or ['supported'])
 return Chatbot(store,client,SimpleNamespace()),client

class AvailabilityTests(unittest.TestCase):
 def test_existing_topics_default_to_supported(self):
  self.assertTrue(is_service_topic({}));self.assertFalse(is_service_topic({'service_status':'unsupported_draft'}))
 def test_list_separates_research_draft(self):
  bot,_=make_bot();r=bot.topic_listing()
  self.assertEqual([t['id'] for t in r['topics']],['supported'])
  self.assertEqual(r['unsupported_topics'][0]['reason'],'대표 근거 준비 중')
  self.assertNotIn('path',r['unsupported_topics'][0])
 def test_explicit_draft_fails_before_model_call(self):
  bot,client=make_bot()
  with self.assertRaises(TopicUnavailableError):bot.answer('질문',selected_ids=['draft'])
  self.assertEqual(client.calls,[])
 def test_draft_cannot_enter_query_planning(self):
  bot,client=make_bot()
  with self.assertRaises(TopicUnavailableError):bot.plan_query('질문',[],['draft'])
  self.assertEqual(client.calls,[])
 def test_auto_catalog_excludes_draft(self):
  bot,client=make_bot();r,_=bot.choose_topics('질문',[],'질문')
  self.assertEqual([t['id'] for t in client.calls[0]['catalog']],['supported'])
  self.assertEqual(r['selected_ids'],['supported'])
 def test_guessed_draft_id_is_rejected(self):
  bot,client=make_bot(['draft'])
  with self.assertRaises(TopicUnavailableError):bot.choose_topics('질문',[],'질문')
 def test_actual_service_topics_all_have_representative_evidence(self):
  topics,parents=load_data(REPO)
  supported={k:t for k,t in topics.items() if is_service_topic(t)}
  drafts={k:t for k,t in topics.items() if not is_service_topic(t)}
  self.assertEqual(len(topics),103);self.assertEqual(len(supported),101)
  self.assertEqual(set(drafts),{'internet_renewal_comparison','internet_sales_dispute'})
  for k,t in supported.items():
   self.assertTrue(t['primary_chunk_ids'],k)
   self.assertTrue(any(not parents[c]['meta'].get('extraction_quality_flags') for c in t['primary_chunk_ids']),k)
  self.assertTrue(all(not t['retrieval_ready'] for t in drafts.values()))

if __name__=='__main__':unittest.main()
