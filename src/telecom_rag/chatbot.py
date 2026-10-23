"""Two-node LangGraph RAG with structured planning, candidate filtering and citations."""
import hashlib
import json
import time
from pathlib import Path
from typing import TypedDict, Any
from langgraph.graph import StateGraph, START, END
from .gms import GMSClient, GMSClientError
from .settings import GMSSettings
from .external import ExternalLookup, official_url
from .answer_validation import validate_answer
from .availability import is_service_topic, TopicUnavailableError
from .source_presentation import evidence_presentation, topic_context


def named_product_sources(parents, question):
    normalized=''.join(question.split()).casefold()
    return [p for p in parents.values() if p['document_id'].startswith(('kt_bundle_','kt_plan_','kt_mobile_'))
            and len(''.join(p['title'].split()))>=4
            and ''.join(p['title'].split()).casefold() in normalized
            and not p['meta'].get('extraction_quality_flags')]


class State(TypedDict, total=False):
    question: str
    history: list
    explicit_ids: list
    external_requested: bool
    started: float
    plan: dict
    choice: dict
    retrieved: dict
    trace: list
    usage: dict
    result: dict


class Chatbot:
    def __init__(self,store,client=None,external=None):
        self.store=store
        self.client=client or GMSClient(GMSSettings.load(store.repo))
        self.config=json.loads((store.repo/'config/chatbot.json').read_text(encoding='utf-8-sig'))
        self.prompts={name:(store.repo/'prompts'/name).read_text(encoding='utf-8-sig') for name in ['01_chat_query.md','02_topic_select.md','02_document_select.md','03_generate.md']}
        self.external=external or ExternalLookup(store,self.config)
        self.progress=lambda stage:None
        graph=StateGraph(State)
        graph.add_node('retrieve',self.retrieve_node)
        graph.add_node('generate',self.generate_node)
        graph.add_edge(START,'retrieve');graph.add_edge('retrieve','generate');graph.add_edge('generate',END)
        self.graph=graph.compile()

    def _json(self,prompt,data,tokens=1200):
        for attempt in range(2):
            try:
                response=self.client.respond(json.dumps(data,ensure_ascii=False),instructions=self.prompts[prompt],max_output_tokens=tokens)
                break
            except GMSClientError as exc:
                if attempt or exc.status_code not in {502,503,504}:raise
                self.progress('모델 연결 오류로 한 번 재시도 중')
                time.sleep(1)
        value=json.loads(response.text)
        if not isinstance(value,dict):raise ValueError('object_required')
        return value,response.usage

    def bounded_query(self,text):
        # Safe truncation is explicit and affects search only; full question still reaches generation.
        tokenizer=self.store.engine.tokenizer
        spans=tokenizer.encode(text,add_special_tokens=False).offsets
        return text[:spans[469][1]] if len(spans)>470 else text

    def choose_topics(self,question,history,query):
        ranked=self.store.search_topics(self.bounded_query(query),k=25)
        # Full compact catalog remains as recall fallback while semantic ranking is under review.
        order=[i for i in dict.fromkeys([r['item_id'] for r in ranked]+list(self.store.topics)) if is_service_topic(self.store.topics[i])]
        catalog=[{'id':k,'name':self.store.topics[k]['name'],'summary':self.store.topics[k]['summary'][:150]} for k in order]
        value,usage=self._json('02_topic_select.md',{'question':question,'history':history,'catalog':catalog})
        ids=value.get('selected_ids')
        if not isinstance(ids,list) or len(ids)>4 or any(not isinstance(x,str) or x not in self.store.topics for x in ids) or not isinstance(value.get('reason'),str):raise ValueError('selection_invalid')
        if any(not is_service_topic(self.store.topics[i]) for i in ids):raise TopicUnavailableError()
        value['selected_ids']=list(dict.fromkeys(ids))
        return value,usage

    def explore(self,question):
        if not isinstance(question,str) or not question.strip() or len(question)>6000:raise ValueError('question_invalid')
        choice,_=self.choose_topics(question,[],question)
        return {'topics':[self.topic_card(i) for i in choice['selected_ids']],'reason':choice['reason']}

    def topic_card(self,i):
        t=self.store.topics[i]
        return {'id':i,'name':t['name'],'category':t.get('category',''),'summary':t['summary'],'evidence_status':t['evidence_status'],'example_questions':t.get('example_questions',[])}

    def topic_listing(self):
        active=[];unsupported=[]
        for item_id,topic in self.store.topics.items():
            card=self.topic_card(item_id)
            if is_service_topic(topic):active.append(card)
            else:unsupported.append({**card,'service_status':'unsupported_draft','reason':topic.get('support_reason','대표 공식 근거 준비 중')})
        return {'topics':active,'unsupported_topics':unsupported}

    def plan_query(self,question,history,selected_ids):
        # Topic metadata disambiguates the question; it cannot establish policy facts.
        if not isinstance(selected_ids,list) or len(selected_ids)>4 or any(not isinstance(i,str) or i not in self.store.topics for i in selected_ids):
            raise ValueError('topic_invalid')
        if any(not is_service_topic(self.store.topics[i]) for i in selected_ids):raise TopicUnavailableError()
        topics=[]
        for item_id in dict.fromkeys(selected_ids):
            topic=self.store.topics[item_id]
            topics.append({'item_id':item_id,'name':topic['name'],
                           'summary':topic['summary'],'scope':topic.get('scope',''),
                           'service_types':topic.get('service_types',[]),
                           'condition_keys':topic.get('condition_keys',[]),
                           'is_policy_evidence':False})
        plan,usage=self._json('01_chat_query.md',{'question':question,'history':history,'selected_topics':topics})
        if set(plan)!={'retrieval_query','external_queries','needs_external','reason'} or not isinstance(plan['retrieval_query'],str) or not plan['retrieval_query'].strip() or len(plan['retrieval_query'])>300 or type(plan['needs_external']) is not bool or not isinstance(plan['external_queries'],list) or len(plan['external_queries'])>2 or any(not isinstance(x,str) or len(x)>100 for x in plan['external_queries']) or not isinstance(plan['reason'],str):raise ValueError('plan_invalid')
        return plan,usage

    def retrieve_node(self,state):
        q,h=state['question'],state['history'];usage={};trace=[]
        self.progress('관련 상담 주제 선별 중')
        if state['explicit_ids']:
            choice={'selected_ids':state['explicit_ids'],'reason':'사용자가 선택한 상담 주제'}
        else:choice,usage['selection']=self.choose_topics(q,h,q)
        ids=choice['selected_ids']
        self.progress('질문과 선택한 상담 주제 분석 중')
        plan,usage['planning']=self.plan_query(q,h,ids)
        query=self.bounded_query(plan['retrieval_query'])
        if not ids:return {'plan':plan,'choice':choice,'retrieved':{'evidence':[],'topic_metadata':[],'warnings':[]},'trace':trace,'usage':usage}
        self.progress('공식 문서 검색 중')
        retrieved=self.store.retrieve(query,ids)
        named=named_product_sources(getattr(self.store,'parents',{}),q+' '+query)
        found={e['parent_chunk_id'] for e in retrieved['evidence']}
        for p in named:
            if p['chunk_id'] not in found:
                retrieved['evidence'].append({'parent_chunk_id':p['chunk_id'],'document_id':p['document_id'],'document_version':p['version'],'title':p['title'],'source_url':p['source_url'],'text':p['body'],'source_pages':p['meta'].get('source_pages',[]),'role':'named_product'})
                found.add(p['chunk_id'])
        if named:trace.append({'kind':'named_product_sources','titles':list(dict.fromkeys(p['title'] for p in named)),'chunks':len(named)})
        external_needed=state['external_requested'] or plan['needs_external'] or not retrieved['evidence']
        if external_needed and self.config['external_enabled']:
            self.progress('공식 외부 문서 후보 조회 중')
            search_queries=plan['external_queries'] or ['KT '+self.store.topics[ids[0]]['name']]
            candidates,events=self.external.discover(search_queries,ids);trace+=events
            mapped={'C'+str(i+1):c for i,c in enumerate(candidates)}
            chosen=[]
            if mapped:
                decision,usage['document_selection']=self._json('02_document_select.md',{'question':q,'selected_topics':[self.topic_card(i) for i in ids],'candidates':[{'candidate_id':k,**{f:c[f] for f in ['title','url','summary','origin']}} for k,c in mapped.items()]})
                chosen=decision.get('selected_candidate_ids')
                if not isinstance(chosen,list) or len(chosen)>2 or any(not isinstance(x,str) or x not in mapped for x in chosen):raise ValueError('document_selection_invalid')
                trace.append({'kind':'candidate_selection','selected':[mapped[k]['url'] for k in chosen],'reason':decision.get('reason','')})
            for key in list(dict.fromkeys(chosen))[:self.config['max_fetch_documents']]:
                c=mapped[key]
                if c['origin']=='official_bundle':
                    # Reuse the saved official source bundle when live access is unnecessary/unavailable.
                    for cid in c['parent_ids']:
                        if cid not in {e['parent_chunk_id'] for e in retrieved['evidence']}:
                            p=self.store.parents[cid]
                            if p['meta'].get('extraction_quality_flags'):continue
                            retrieved['evidence'].append({'parent_chunk_id':cid,'document_id':p['document_id'],'document_version':p['version'],'title':p['title'],'source_url':p['source_url'],'text':p['body'],'source_pages':p['meta'].get('source_pages',[]),'role':'external_bundle'})
                    trace.append({'kind':'saved_official_bundle','url':c['url']});continue
                try:
                    self.progress('선별된 공식 문서 수집·색인 중')
                    doc=self.external.fetch(c['url']);self.external.index_document(doc,ids)
                    trace.append({'kind':'document_cache_hit' if doc['cache_hit'] else 'document_fetched_indexed','url':doc['source_url'],'fetched_at':doc['created_at']})
                except Exception as exc:
                    # Never expose headers, raw provider messages or stack traces.
                    trace.append({'kind':'document_unavailable','url':c['url'],'code':str(exc) if isinstance(exc,ValueError) else type(exc).__name__})
        live=self.external.search_index(query,ids)
        keys={(e['source_url'],hashlib.sha256(e['text'].encode()).hexdigest()) for e in retrieved['evidence']}
        for e in live:
            key=(e['source_url'],hashlib.sha256(e['text'].encode()).hexdigest())
            if key not in keys:retrieved['evidence'].append(e);keys.add(key)
        # Representatives always survive; optional docs fit the configured context budget.
        kept=[];count=0
        for e in retrieved['evidence']:
            if e['role']=='representative' or count+len(e['text'])<=self.config['max_context_chars']:
                kept.append(e);count+=len(e['text'])
        if len(kept)<len(retrieved['evidence']):trace.append({'kind':'optional_context_limited'})
        retrieved['evidence']=kept
        return {'plan':plan,'choice':choice,'retrieved':retrieved,'trace':trace,'usage':usage}

    def generate_node(self,state):
        self.progress('근거를 바탕으로 답변 작성 중')
        sources={'E'+str(i+1):{**e,**evidence_presentation(e,getattr(self.store,'parents',{}).get(e['parent_chunk_id']))} for i,e in enumerate(state['retrieved']['evidence'])}
        ids=state['choice']['selected_ids'];usage=state['usage']
        if sources:
            payload={'question':state['question'],'history':state['history'],'topic_metadata':state['retrieved']['topic_metadata'],'evidence':sources,'external_lookup':state['trace']}
            data,usage['generation']=self._json('03_generate.md',payload,4000)
            self.progress('인용 원문과 추론 고지 검사 중')
            try:
                answer=validate_answer(data,sources)
            except ValueError as exc:
                self.progress('인용 표기를 한 번 보정한 뒤 재검사 중')
                payload.update(previous_answer=data,validation_error=str(exc),repair_instruction='검증 실패를 수정한다. 인용 문구를 원문에서 그대로 복사하고 추론 고지를 정확히 넣는다. 근거 없는 주장은 삭제한다.')
                repaired,usage['generation_repair']=self._json('03_generate.md',payload,4000)
                answer=validate_answer(repaired,sources)
        else:
            answer={'claims':[],'follow_up':'현재 확보한 공식 자료에서 답변 근거를 확인하지 못했습니다. 정확한 상품명이나 KT 공식 상담을 통해 추가 확인이 필요합니다.'}
        used=list(dict.fromkeys(c['id'] for claim in answer['claims'] for c in claim['citations']))
        public=[]
        for sid in used:
            e=sources[sid]
            public.append({'id':sid,'title':e['title'],'url':e['source_url'] if official_url(e['source_url']) else '', 'parent_chunk_id':e['parent_chunk_id'],'pages':e.get('source_pages',[]),'source_type':e['source_type'],'source_type_label':e['source_type_label'],'source_format':e['source_format'],'source_origin':e['source_origin'],'source_origin_label':e['source_origin_label'],'fetched_at':e.get('fetched_at')})
        context=topic_context([{'item_id':i,**self.store.topics[i]} for i in ids])
        result={**answer,'sources':public,'topic_context':context,'selected_topics':[{'id':i,'name':self.store.topics[i]['name']} for i in ids],
                'selection_reason':state['choice']['reason'],'warnings':state['retrieved']['warnings'],'external_lookup':state['trace'],
                'validation':{'citation_ids_and_quotes':True,'inference_disclosure':True,'semantic_entailment':'manual_review_required'},
                'elapsed_seconds':round(time.monotonic()-state['started'],2),'usage':usage,'pipeline':'LangGraph: retrieve → generate'}
        return {'result':result}

    def answer(self,question,history=None,selected_ids=None,external_requested=False,progress=None):
        if not isinstance(question,str) or not question.strip() or len(question)>6000:raise ValueError('question_invalid')
        history=[] if history is None else history
        if not isinstance(history,list) or len(history)>12 or any(not isinstance(x,dict) or x.get('role') not in {'user','assistant'} or not isinstance(x.get('content'),str) or len(x['content'])>12000 for x in history):raise ValueError('history_invalid')
        selected_ids=[] if selected_ids is None else selected_ids
        if not isinstance(selected_ids,list) or len(selected_ids)>4 or any(not isinstance(i,str) or i not in self.store.topics for i in selected_ids):raise ValueError('topic_invalid')
        if any(not is_service_topic(self.store.topics[i]) for i in selected_ids):raise TopicUnavailableError()
        if type(external_requested) is not bool:raise ValueError('external_invalid')
        self.progress=progress or (lambda stage:None)
        try:
            return self.graph.invoke({'question':question,'history':history[-6:],'explicit_ids':list(dict.fromkeys(selected_ids)),'external_requested':external_requested,'started':time.monotonic()})['result']
        finally:self.progress=lambda stage:None
