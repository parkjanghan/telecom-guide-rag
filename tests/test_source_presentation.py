import json,time,unittest
from pathlib import Path
from types import SimpleNamespace
from telecom_rag.source_presentation import evidence_presentation,topic_context
from telecom_rag.chatbot import Chatbot
from telecom_rag.core import load_data
from telecom_rag.gms import GMSResponse

REPO=Path(__file__).resolve().parents[1]

class SourcePresentationTests(unittest.TestCase):
 def test_static_types_from_original_paths(self):
  cases=[('faq','official_faq'),('service_guides','service_guide'),('bundles','product_detail'),('mobile_plans','product_detail'),('payment_benefits','payment_benefit_guide'),('discounts','discount_guide')]
  for folder,expected in cases:
   with self.subTest(folder=folder):self.assertEqual(evidence_presentation({'source_path':'data/chunks/'+folder+'/a.md'})['source_type'],expected)
 def test_pdf_is_not_always_a_terms_document(self):
  self.assertEqual(evidence_presentation({'source_type':'pdf','title':'KT 이용약관'})['source_type'],'terms_pdf')
  self.assertEqual(evidence_presentation({'source_type':'pdf','title':'KT 서비스 신청서'})['source_type'],'official_pdf')
 def test_parent_metadata_covers_named_product_without_path(self):
  self.assertEqual(evidence_presentation({}, {'path':'data/chunks/bundles/a.md','meta':{}})['source_type'],'product_detail')
 def test_live_source_keeps_its_origin(self):
  value=evidence_presentation({'source_type':'html','source_url':'https://ermsweb.kt.com/pc/faq/a','role':'external_live'})
  self.assertEqual(value['source_type'],'official_faq');self.assertEqual(value['source_origin'],'external_lookup')
 def test_unknown_source_is_not_guessed_as_product(self):
  self.assertEqual(evidence_presentation({'title':'안내'})['source_type'],'official_web')
 def test_topic_context_is_not_policy_and_has_no_citation_id(self):
  result=topic_context([{'item_id':'x','name':'주제','summary':'설명','path':'private','is_policy_evidence':True}])[0]
  self.assertFalse(result['is_policy_evidence']);self.assertEqual(result['source_type'],'topic_metadata')
  self.assertNotIn('id',result);self.assertNotIn('path',result);self.assertNotIn('source_url',result)
 def test_real_corpus_has_a_display_type(self):
  _,parents=load_data(REPO)
  for p in parents.values():
   value=evidence_presentation({'title':p['title'],'source_url':p['source_url']},p)
   self.assertTrue(value['source_type_label'],p['chunk_id'])
   if p['path'].startswith('data/chunks/faq/'):
    self.assertEqual(value['source_type'],'official_faq')
   if p['path'].startswith('data/chunks/terms/'):
    self.assertEqual(value['source_format'],'PDF')
 def test_generation_returns_only_cited_sources_and_separate_metadata(self):
  class Client:
   def respond(self,text,**kwargs):
    self.payload=json.loads(text)
    return GMSResponse(json.dumps({'claims':[{'text':'원문에서 확인한 설명','inferred':False,'citations':[{'id':'E1','quote':'본인 인증 후 변경 가능합니다.'}]}],'follow_up':''}),'test','completed',{})
  topic={'item_id':'t','name':'납부수단 변경','summary':'변경 상담','scope':'납부','is_policy_evidence':True}
  client=Client();store=SimpleNamespace(repo=REPO,topics={'t':topic},parents={})
  bot=Chatbot(store,client,SimpleNamespace())
  evidence=[{'parent_chunk_id':'faq1','source_path':'data/chunks/faq/a.md','source_url':'https://ermsweb.kt.com/a','title':'FAQ','text':'본인 인증 후 변경 가능합니다.'}, {'parent_chunk_id':'guide1','source_path':'data/chunks/service_guides/a.md','source_url':'https://help.kt.com/a','title':'가이드','text':'사용하지 않은 근거'}]
  result=bot.generate_node({'question':'질문','history':[],'retrieved':{'evidence':evidence,'topic_metadata':[topic],'warnings':[]},'choice':{'selected_ids':['t'],'reason':'test'},'usage':{},'trace':[],'started':time.monotonic()})['result']
  self.assertEqual([s['id'] for s in result['sources']],['E1'])
  self.assertEqual(result['sources'][0]['source_type_label'],'공식 FAQ')
  self.assertFalse(result['topic_context'][0]['is_policy_evidence'])
  self.assertEqual(client.payload['evidence']['E2']['source_type_label'],'공식 서비스 가이드')

if __name__=='__main__':unittest.main()
