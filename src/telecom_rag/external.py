"""Official-source discovery, bounded fetch, TTL cache and shared evidence indexing."""
import hashlib
import io
import json
import time
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET
import httpx
from bs4 import BeautifulSoup
from .core import split_offsets

HOSTS={'rdi.kt.com','help.kt.com','product.kt.com','ermsweb.kt.com','www.kt.com','kt.com','shop.kt.com','m.shop.kt.com','m.kt.com','corp.kt.com','enterprise.kt.com'}
UA='TelecomGuideRAG/0.1 (educational local research; limited official-document lookup)'

def official_url(url):
    if not isinstance(url,str): return False
    p=urlparse(url)
    try: port=p.port
    except ValueError: return False
    return p.scheme=='https' and p.hostname in HOSTS and port in {None,443} and not p.username and not p.password and not p.fragment


def extract_body(raw, content_type, url):
    if 'pdf' in content_type or raw[:4]==b'%PDF':
        from pypdf import PdfReader
        pages=PdfReader(io.BytesIO(raw)).pages
        if len(pages)>400: raise ValueError('pdf_too_large')
        text='\n\n'.join(f'[PDF {i+1}쪽]\n'+(p.extract_text() or '') for i,p in enumerate(pages))
        return urlparse(url).path.rsplit('/',1)[-1],text,'pdf'
    soup=BeautifulSoup(raw,'html.parser')
    title=soup.title.get_text(' ',strip=True) if soup.title else url
    for node in soup(['script','style','nav','header','footer','noscript','iframe','form']): node.decompose()
    body=soup.select_one('main, article, #contents, #content, .contents') or soup.body or soup
    text=body.get_text('\n',strip=True)
    return title,text,'html'


class ExternalLookup:
    def __init__(self, store, config, transport=None, clock=time.time):
        self.store,self.config,self.transport,self.clock=store,config,transport,clock
        self.root=store.runtime/'external'; self.root.mkdir(parents=True,exist_ok=True)
        self.robots={}; self.last_request=0

    def _cache_path(self,kind,key):
        return self.root/(kind+'_'+hashlib.sha256(key.encode()).hexdigest()+'.json')

    def _read(self,path,ttl):
        try:
            value=json.loads(path.read_text(encoding='utf-8'))
            if 0<=self.clock()-value['created_at']<ttl: return value
        except (OSError,ValueError,KeyError,TypeError): pass
        return None

    def _get(self,url):
        # Requests are serialized by the app worker; maintain a per-request minimum interval.
        delay=self.config['request_interval_seconds']-(time.monotonic()-self.last_request)
        if delay>0: time.sleep(delay)
        self.last_request=time.monotonic()
        with httpx.Client(timeout=self.config['timeout_seconds'],follow_redirects=False,transport=self.transport) as client:
            with client.stream('GET',url,headers={'User-Agent':UA}) as response:
                content=bytearray()
                for part in response.iter_bytes():
                    content.extend(part)
                    if len(content)>self.config['max_download_bytes']: raise ValueError('download_too_large')
                return response.status_code,dict(response.headers),bytes(content)

    def discover(self,queries,selected_ids):
        candidates={}; trace=[]
        # The pre-collected official bundle is a source fallback, not fabricated live retrieval.
        for item_id in selected_ids:
            t=self.store.topics[item_id]
            for cid in t['related_chunk_ids']:
                p=self.store.parents[cid]
                if official_url(p['source_url']):
                    candidates.setdefault(p['source_url'],{'url':p['source_url'],'title':p['title'],'summary':p['section_title'],'origin':'official_bundle','parent_ids':[]})['parent_ids'].append(cid)
        import re
        queries=[q for q in queries if q.strip() and not re.search(r'\d{7,}|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',q)]
        for query in queries[:self.config['max_search_queries']]:
            path=self._cache_path('search',query)
            cached=self._read(path,self.config['search_ttl_seconds'])
            if cached:
                found=cached['candidates']; trace.append({'kind':'search_cache_hit','query':query})
            else:
                try:
                    url=str(httpx.URL('https://www.bing.com/search',params={'format':'rss','q':'site:kt.com '+query}))
                    code,_,raw=self._get(url)
                    if code!=200: raise ValueError('search_http_error')
                    root=ET.fromstring(raw);found=[]
                    for item in root.findall('./channel/item'):
                        link=item.findtext('link','')
                        if official_url(link):found.append({'url':link,'title':item.findtext('title',''),'summary':item.findtext('description','')[:900],'origin':'web_search','parent_ids':[]})
                    # Empty search responses may be temporary; do not turn failure into a permanent cache hit.
                    if found:path.write_text(json.dumps({'created_at':self.clock(),'candidates':found},ensure_ascii=False),encoding='utf-8')
                    trace.append({'kind':'web_search','query':query,'official_candidates':len(found)})
                except (httpx.HTTPError,ValueError,ET.ParseError):
                    found=[];trace.append({'kind':'search_unavailable','query':query})
            for c in found:candidates.setdefault(c['url'],c)
        return list(candidates.values())[:40],trace

    def fetch(self,url):
        if not official_url(url): raise ValueError('url_not_allowed')
        path=self._cache_path('document',url)
        cached=self._read(path,self.config['document_ttl_seconds'])
        if cached:return {**cached,'cache_hit':True}
        original=url
        for _ in range(4):
            parsed=urlparse(url); origin=f'https://{parsed.hostname}'
            if origin not in self.robots:
                code,_,raw=self._get(origin+'/robots.txt')
                if code==404:self.robots[origin]=None
                elif code==200:
                    robot=RobotFileParser();robot.parse(raw.decode('utf-8',errors='replace').splitlines());self.robots[origin]=robot
                else:raise ValueError('robots_unavailable')
            robot=self.robots[origin]
            if robot is not None and not robot.can_fetch(UA,url):raise ValueError('robots_denied')
            code,headers,raw=self._get(url)
            if code in {301,302,303,307,308}:
                url=urljoin(url,headers.get('location',''))
                if not official_url(url):raise ValueError('redirect_not_allowed')
                continue
            if code!=200:raise ValueError('fetch_http_error')
            kind=headers.get('content-type','').lower()
            if not any(x in kind for x in ['html','pdf','text/plain']):raise ValueError('unsupported_content_type')
            title,text,source_type=extract_body(raw,kind,url)
            if len(text.strip())<80 or len(text)>1000000:raise ValueError('invalid_document_size')
            if any(x in title.lower() for x in ['access denied','captcha','로그인']):raise ValueError('non_document_page')
            record={'created_at':self.clock(),'source_url':url,'requested_url':original,'title':title,'text':text,'source_type':source_type,'version':hashlib.sha256(text.encode()).hexdigest()[:16],
                    'usage_status':'unreviewed','usage_note':'Public official page; robots checked. Redistribution permission is not established.'}
            path.write_text(json.dumps(record,ensure_ascii=False),encoding='utf-8')
            return {**record,'cache_hit':False}
        raise ValueError('too_many_redirects')

    def index_document(self,doc,item_ids):
        col=self.store.collections[self.store.config['evidence_collection']]
        key='live_'+hashlib.sha256(doc['source_url'].encode()).hexdigest()[:20]
        existing=col.get(where={'document_id':key},include=['metadatas'])
        linked=set(item_ids)
        for m in existing['metadatas']:
            linked.update(k[6:] for k,v in m.items() if k.startswith('topic_') and v is True)
        size=self.store.config['chunk_size_tokens']; overlap=self.store.config['chunk_overlap_tokens']
        spans=split_offsets(doc['text'],self.store.engine.tokenizer,size,overlap)
        ids=[f'{key}:{doc["version"]}:{a}-{b}' for a,b in spans]
        texts=[doc['text'][a:b] for a,b in spans]
        if len(spans)>1000:raise ValueError('too_many_chunks')
        metadata=[{'document_id':key,'parent_chunk_id':key,'document_version':doc['version'],'source_url':doc['source_url'],'title':doc['title'],'quality_ok':True,'live_document':True,'fetched_at':doc['created_at'],'expires_at':doc['created_at']+self.config['document_ttl_seconds'],'char_start':a,'char_end':b,'source_type':doc['source_type'],**{'topic_'+x:True for x in linked}} for a,b in spans]
        vectors=self.store.engine.embed(texts,'passage')
        for i in range(0,len(ids),128):col.upsert(ids=ids[i:i+128],documents=texts[i:i+128],metadatas=metadata[i:i+128],embeddings=vectors[i:i+128])
        stale=[x for x in existing['ids'] if x not in ids]
        if stale:col.delete(ids=stale)
        return key

    def search_index(self,query,item_ids):
        col=self.store.collections[self.store.config['evidence_collection']]
        flags=[{'topic_'+i:True} for i in item_ids]
        if not flags:return []
        where={'$and':[{'live_document':True},{'expires_at':{'$gt':self.clock()}},flags[0] if len(flags)==1 else {'$or':flags}]}
        if not col.get(where=where,limit=1,include=[])['ids']:return []
        r=col.query(query_embeddings=self.store.engine.embed([query],'query'),where=where,n_results=self.config['external_top_k'],include=['metadatas','documents','distances'])
        out=[]
        for rid,m,text,distance in zip(r['ids'][0],r['metadatas'][0],r['documents'][0],r['distances'][0]):
            out.append({'parent_chunk_id':rid,'document_id':m['document_id'],'document_version':m['document_version'],'title':m['title'],'source_url':m['source_url'],'text':text,'source_pages':[],'source_type':m['source_type'],'fetched_at':m['fetched_at'],'role':'external_live','distance':distance})
        return out
