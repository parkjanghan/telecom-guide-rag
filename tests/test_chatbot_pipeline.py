import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import json
import httpx
from telecom_rag.external import official_url, extract_body, ExternalLookup
from telecom_rag.chatbot import Chatbot
from telecom_rag.gms import GMSResponse

class ExternalTests(unittest.TestCase):
 def test_allowlist(self):
  self.assertTrue(official_url('https://help.kt.com/a'))
  for url in ['http://help.kt.com/a','https://help.kt.com.evil.com/a','https://127.0.0.1/a','https://user:pass@help.kt.com/a','https://help.kt.com:999/a','https://help.kt.com/#x']:
   self.assertFalse(official_url(url))
 def test_html_extract(self):
  _,text,_=extract_body(b'<title>Guide</title><main><p>official body</p><script>bad</script></main>','text/html','https://help.kt.com/a')
  self.assertIn('official body',text);self.assertNotIn('bad',text)
 def config(self):return {'request_interval_seconds':0,'timeout_seconds':1,'max_download_bytes':10000,'document_ttl_seconds':10,'search_ttl_seconds':5,'max_search_queries':1}
 def test_document_cache_ttl(self):
  with TemporaryDirectory() as d:
   calls=[];now=[100.]
   def handler(r):
    calls.append(str(r.url))
    if r.url.path=='/robots.txt':return httpx.Response(404)
    return httpx.Response(200,headers={'content-type':'text/html'},text='<title>Test</title><main>'+('KT official test text. '*10)+'</main>')
   e=ExternalLookup(SimpleNamespace(runtime=Path(d)),self.config(),httpx.MockTransport(handler),lambda:now[0])
   self.assertFalse(e.fetch('https://help.kt.com/a')['cache_hit']);n=len(calls)
   self.assertTrue(e.fetch('https://help.kt.com/a')['cache_hit']);self.assertEqual(len(calls),n)
   now[0]=111;self.assertFalse(e.fetch('https://help.kt.com/a')['cache_hit'])
 def test_unsafe_redirect(self):
  with TemporaryDirectory() as d:
   def handler(r):return httpx.Response(404) if r.url.path=='/robots.txt' else httpx.Response(302,headers={'location':'http://127.0.0.1/private'})
   e=ExternalLookup(SimpleNamespace(runtime=Path(d)),self.config(),httpx.MockTransport(handler))
   with self.assertRaises(ValueError):e.fetch('https://help.kt.com/a')
 def test_robots_denied(self):
  with TemporaryDirectory() as d:
   e=ExternalLookup(SimpleNamespace(runtime=Path(d)),self.config(),httpx.MockTransport(lambda r:httpx.Response(200,text='User-agent: *\nDisallow: /')))
   with self.assertRaises(ValueError):e.fetch('https://help.kt.com/a')

class GraphTests(unittest.TestCase):
 def test_two_nodes_and_missing_evidence(self):
  repo=Path(__file__).resolve().parents[1]
  store=SimpleNamespace(repo=repo,runtime=Path('unused'),topics={'t':{'name':'topic','summary':'test','evidence_status':'missing'}})
  store.retrieve=lambda q,ids:{'evidence':[],'topic_metadata':[store.topics['t']],'warnings':[]}
  store.search_topics=lambda *a,**kw:[{'item_id':'t'}]
  class Tokenizer:
   def encode(self,text,**kw):return SimpleNamespace(offsets=[(i,i+1) for i in range(len(text))])
  store.engine=SimpleNamespace(tokenizer=Tokenizer())
  class Client:
   def respond(self,text,**kwargs):
    v={'retrieval_query':'query','external_queries':[],'needs_external':False,'reason':'test'} if 'retrieval_query' in kwargs['instructions'] else {'selected_ids':['t'],'reason':'test'}
    return GMSResponse(json.dumps(v),'test','completed',{})
  ext=SimpleNamespace(discover=lambda *a:([],[]),search_index=lambda *a:[])
  bot=Chatbot(store,Client(),ext)
  events=[];r=bot.answer('question',progress=events.append)
  self.assertEqual(r['claims'],[]);self.assertEqual(set(bot.graph.get_graph().nodes),{'__start__','retrieve','generate','__end__'})
  self.assertTrue(events)
  self.assertLessEqual(len(bot.bounded_query('가'*3000)),470)
 def test_invalid_history(self):
  bot=object.__new__(Chatbot)
  with self.assertRaises(ValueError):bot.answer('q',history='bad')
  with self.assertRaises(ValueError):bot.answer('q',selected_ids='bad')

if __name__=='__main__':unittest.main()

class ExternalIndexTests(unittest.TestCase):
 def test_upsert_topics_expiry_and_version(self):
  import chromadb,uuid
  with TemporaryDirectory() as d:
   col=chromadb.EphemeralClient().create_collection('test_'+uuid.uuid4().hex,embedding_function=None,metadata={'hnsw:space':'cosine'})
   class Tokenizer:
    def encode(self,text,**kwargs):return SimpleNamespace(offsets=[(i,i+1) for i in range(len(text))])
   engine=SimpleNamespace(tokenizer=Tokenizer(),embed=lambda texts,kind:[[1.,0.,0.] for _ in texts])
   store=SimpleNamespace(runtime=Path(d),config={'evidence_collection':'docs','chunk_size_tokens':30,'chunk_overlap_tokens':5},collections={'docs':col},engine=engine)
   now=[100.];cfg={'document_ttl_seconds':10,'external_top_k':3}
   ext=ExternalLookup(store,cfg,clock=lambda:now[0])
   doc={'source_url':'https://help.kt.com/test','text':'official body '*8,'version':'v1','title':'Test','created_at':100.,'source_type':'html'}
   ext.index_document(doc,['a']);count=col.count()
   ext.index_document(doc,['b']);self.assertEqual(count,col.count())
   self.assertTrue(all(m['topic_a'] and m['topic_b'] for m in col.get(include=['metadatas'])['metadatas']))
   self.assertTrue(ext.search_index('query',['b']))
   now[0]=111.;self.assertFalse(ext.search_index('query',['b']))
   doc.update(text='new official text '*4,version='v2',created_at=111.)
   ext.index_document(doc,['b']);self.assertTrue(all(':v2:' in x for x in col.get(include=[])['ids']))
   self.assertTrue(ext.search_index('query',['a']))

class RepairTests(unittest.TestCase):
 def test_bad_quote_repaired_once(self):
  repo=Path(__file__).resolve().parents[1]
  store=SimpleNamespace(repo=repo,runtime=Path('unused'),topics={'t':{'name':'topic','summary':'test','evidence_status':'linked_draft'}})
  evidence={'text':'KT 본인 인증 후 변경 가능합니다.','role':'representative','title':'Test','source_url':'https://help.kt.com/test','parent_chunk_id':'p','source_pages':[]}
  store.retrieve=lambda q,ids:{'evidence':[evidence],'topic_metadata':[store.topics['t']],'warnings':[]}
  store.engine=SimpleNamespace(tokenizer=SimpleNamespace(encode=lambda text,**kw:SimpleNamespace(offsets=[(i,i+1) for i in range(len(text))])))
  plan={'retrieval_query':'query','external_queries':[],'needs_external':False,'reason':'test'}
  bad={'claims':[{'text':'변경 가능','inferred':False,'citations':[{'id':'E1','quote':'원문에 없는 잘못된 인용입니다'}]}],'follow_up':''}
  good={'claims':[{'text':'변경 가능','inferred':False,'citations':[{'id':'E1','quote':'KT 본인 인증 후 변경 가능합니다.'}]}],'follow_up':''}
  class Client:
   def __init__(self):self.responses=[plan,bad,good];self.calls=0
   def respond(self,*a,**kw):
    self.calls+=1;return GMSResponse(json.dumps(self.responses.pop(0)),'test','completed',{})
  client=Client();ext=SimpleNamespace(search_index=lambda *a:[])
  bot=Chatbot(store,client,ext);r=bot.answer('q',selected_ids=['t'])
  self.assertEqual(client.calls,3);self.assertIn('generation_repair',r['usage']);self.assertEqual(len(r['sources']),1)

class NamedProductTests(unittest.TestCase):
 def test_exact_named_product(self):
  from telecom_rag.chatbot import named_product_sources
  p={'document_id':'kt_bundle_x','title':'프리미엄 싱글결합','meta':{}}
  self.assertEqual(named_product_sources({'p':p},'프리미엄싱글결합을 유지하고 싶어요'),[p])
  self.assertEqual(named_product_sources({'p':p},'프리미엄 가족결합을 쓰고 있어요'),[])
 def test_quarantined_product(self):
  from telecom_rag.chatbot import named_product_sources
  p={'document_id':'kt_bundle_x','title':'총액 결합할인','meta':{'extraction_quality_flags':['bad']}}
  self.assertEqual(named_product_sources({'p':p},'총액 결합할인'),[])

class TransientRetryTests(unittest.TestCase):
 def test_transient_retry_is_bounded(self):
  from telecom_rag.gms import GMSClientError
  from unittest.mock import patch
  bot=object.__new__(Chatbot);bot.prompts={'p':'test'};bot.progress=lambda x:None
  class Client:
   def __init__(self):self.calls=0
   def respond(self,*a,**kw):
    self.calls+=1;raise GMSClientError('http_error',502)
  bot.client=Client()
  with patch('telecom_rag.chatbot.time.sleep'):
   with self.assertRaises(GMSClientError):bot._json('p',{})
  self.assertEqual(bot.client.calls,2)
 def test_rate_limit_does_not_retry(self):
  from telecom_rag.gms import GMSClientError
  bot=object.__new__(Chatbot);bot.prompts={'p':'test'};bot.progress=lambda x:None
  class Client:
   def __init__(self):self.calls=0
   def respond(self,*a,**kw):self.calls+=1;raise GMSClientError('http_error',429)
  bot.client=Client()
  with self.assertRaises(GMSClientError):bot._json('p',{})
  self.assertEqual(bot.client.calls,1)
