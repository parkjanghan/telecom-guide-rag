import json
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock
import httpx
from telecom_rag.webapp import create_server
from telecom_rag.external import ExternalLookup

REPO=Path('C:/SSAFY/workspace/telecom-guide-rag')

class HttpBoundaries(unittest.TestCase):
 def run_server(self,ready=True,index=True):
  store=SimpleNamespace(check_index=lambda:None,topics={'a':{}},parents={'p':{}})
  def factory(*args):
   if not index:raise ValueError('private internal path')
   return store
  bot=SimpleNamespace(topic_listing=lambda:{'topics':[{'id':'a'}],'unsupported_topics':[]},answer=lambda *a,**k:{'claims':[]},explore=lambda q:{})
  server=create_server(REPO,REPO/'.runtime',0,settings_loader=lambda p:SimpleNamespace(status=lambda:{'ready':ready}),store_factory=factory,bot_factory=lambda s:bot)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
  return httpx.Client(base_url='http://127.0.0.1:'+str(server.server_port),trust_env=False)
 def test_missing_key(self):
  with self.run_server(ready=False) as c:
   self.assertEqual(c.get('/').status_code,200)
   self.assertEqual(c.get('/api/health').json()['error'],'settings_not_ready')
   r=c.post('/api/chat',json={'question':'test'})
   self.assertEqual(r.status_code,503);self.assertEqual(r.json(),{'error':'settings_not_ready'})
 def test_missing_index(self):
  with self.run_server(index=False) as c:
   self.assertEqual(c.get('/api/health').json()['error'],'index_not_ready')
   self.assertEqual(c.post('/api/chat',json={}).status_code,503)
 def test_origin_and_json(self):
  with self.run_server() as c:
   self.assertEqual(c.get('/api/health',headers={'Origin':'https://evil.example'}).status_code,403)
   self.assertEqual(c.post('/api/chat',content='x').status_code,415)
   self.assertEqual(c.post('/api/chat',content='[]',headers={'Content-Type':'application/json'}).status_code,400)
   self.assertEqual(c.post('/api/chat',json={'question':'test'}).status_code,200)

class CacheBoundaries(unittest.TestCase):
 def test_empty_success_cached_but_expired(self):
  with TemporaryDirectory() as d:
   calls=[];now=[100.]
   def handler(r):calls.append(1);return httpx.Response(200,text='<rss><channel/></rss>')
   cfg={'request_interval_seconds':0,'timeout_seconds':1,'max_download_bytes':10000,'search_ttl_seconds':100,'empty_search_ttl_seconds':5,'max_search_queries':1}
   ext=ExternalLookup(SimpleNamespace(runtime=Path(d)),cfg,httpx.MockTransport(handler),lambda:now[0])
   ext.discover(['test'],[]);ext.discover(['test'],[])
   self.assertEqual(len(calls),1)
   now[0]=106.;ext.discover(['test'],[]);self.assertEqual(len(calls),2)
 def test_failed_search_not_cached(self):
  with TemporaryDirectory() as d:
   calls=[]
   def handler(r):calls.append(1);return httpx.Response(503)
   cfg={'request_interval_seconds':0,'timeout_seconds':1,'max_download_bytes':10000,'search_ttl_seconds':100,'max_search_queries':1}
   ext=ExternalLookup(SimpleNamespace(runtime=Path(d)),cfg,httpx.MockTransport(handler))
   ext.discover(['test'],[]);ext.discover(['test'],[]);self.assertEqual(len(calls),2)
 def test_identical_document_skips_embedding_and_upsert(self):
  with TemporaryDirectory() as d:
   values={'ids':[],'metadatas':[]}
   def upsert(**kw):values.update(ids=kw['ids'],metadatas=kw['metadatas'])
   col=SimpleNamespace(get=lambda **kw:values,upsert=Mock(side_effect=upsert),delete=Mock())
   engine=SimpleNamespace(tokenizer=SimpleNamespace(encode=lambda t,**kw:SimpleNamespace(offsets=[(i,i+1) for i in range(len(t))])),embed=Mock(side_effect=lambda t,k:[[1.,0.] for _ in t]))
   store=SimpleNamespace(runtime=Path(d),config={'evidence_collection':'docs','chunk_size_tokens':30,'chunk_overlap_tokens':5},collections={'docs':col},engine=engine)
   ext=ExternalLookup(store,{'document_ttl_seconds':10})
   doc={'source_url':'https://help.kt.com/test','text':'official text '*5,'version':'v1','title':'Test','created_at':100.,'source_type':'html'}
   ext.index_document(doc,['a']);ext.index_document(doc,['a'])
   self.assertEqual(engine.embed.call_count,1);self.assertEqual(col.upsert.call_count,1)
   ext.index_document(doc,['b']);self.assertEqual(col.upsert.call_count,2)
   self.assertTrue(all(m['topic_a'] and m['topic_b'] for m in values['metadatas']))

if __name__=='__main__':unittest.main()
