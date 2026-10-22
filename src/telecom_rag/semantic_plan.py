"""GMS-backed question planning. Grounding checks are not semantic correctness proofs."""
from pathlib import Path
import hashlib
import json
import time
from .gms import GMSClient
from .settings import GMSSettings

SERVICES={'모바일','인터넷','TV','와이파이','집전화','미확인'}
OPERATORS={'KT','KT M모바일','SKT','SK브로드밴드','LG U+','기타','미확인'}

class SemanticPlanError(ValueError):
    pass


def validate_plan(value, question):
    if not isinstance(value,dict) or set(value)!={'schema_version','intents','facts','constraints','unknowns'}:
        raise SemanticPlanError('invalid_plan_fields')
    if value['schema_version']!='1.0':raise SemanticPlanError('invalid_schema_version')
    def text(x):return isinstance(x,str) and bool(x.strip())
    def quote(x):
        if not text(x) or x not in question:raise SemanticPlanError('ungrounded_quote')
    intents=value['intents']
    if not isinstance(intents,list) or not 1<=len(intents)<=4:raise SemanticPlanError('invalid_intent_count')
    for intent in intents:
        if not isinstance(intent,dict) or set(intent)!={'goal','search_query','services','operators','evidence_quotes'}:
            raise SemanticPlanError('invalid_intent_fields')
        if not text(intent['goal']) or not text(intent['search_query']) or len(intent['search_query'])>800:
            raise SemanticPlanError('invalid_intent_text')
        for key,allowed in [('services',SERVICES),('operators',OPERATORS)]:
            if not isinstance(intent[key],list) or not intent[key] or any(not isinstance(v,str) or v not in allowed for v in intent[key]):
                raise SemanticPlanError('invalid_service_or_operator')
        if not isinstance(intent['evidence_quotes'],list) or not intent['evidence_quotes']:raise SemanticPlanError('missing_intent_quotes')
        for q in intent['evidence_quotes']:quote(q)
    for key in ['facts','constraints']:
        if not isinstance(value[key],list) or len(value[key])>20:raise SemanticPlanError('invalid_context_list')
        for row in value[key]:
            keys={'key','value','quote'} if key=='facts' else {'kind','text','quote'}
            if not isinstance(row,dict) or set(row)!=keys:raise SemanticPlanError('invalid_context_fields')
            if any(not text(row[k]) for k in keys):raise SemanticPlanError('invalid_context_text')
            quote(row['quote'])
            if key=='constraints' and row['kind'] not in {'preserve','exclude','compare'}:
                raise SemanticPlanError('invalid_constraint_kind')
    if not isinstance(value['unknowns'],list) or len(value['unknowns'])>12 or any(not text(v) for v in value['unknowns']):
        raise SemanticPlanError('invalid_unknowns')
    return value


def retrieval_queries(question, plan):
    queries=[{'text':question,'kind':'whole'}]
    seen={question}
    for intent in plan['intents']:
        if intent['search_query'] not in seen:
            queries.append({'text':intent['search_query'],'kind':'semantic',
                            'goal':intent['goal'],'evidence_quotes':intent['evidence_quotes']})
            seen.add(intent['search_query'])
    return queries


class SemanticPlanner:
    def __init__(self, repo:Path, client=None, cache_dir:Path|None=None):
        self.repo=repo
        self.client=client or GMSClient(GMSSettings.load(repo))
        self.cache_dir=cache_dir or repo/'.runtime/semantic_plans'
        self.prompt=(repo/'prompts/01_search_plan.md').read_text(encoding='utf-8-sig')

    def plan(self,question:str):
        if not isinstance(question,str) or not question.strip() or len(question)>6000:
            raise SemanticPlanError('invalid_question_length')
        model=self.client.settings.model
        signature=json.dumps([model,self.client.settings.api_url,self.prompt,question],ensure_ascii=False)
        cache_key=hashlib.sha256(signature.encode()).hexdigest()
        path=self.cache_dir/(cache_key+'.json')
        if path.exists():
            try:cached=json.loads(path.read_text(encoding='utf-8'))
            except (ValueError,OSError):raise SemanticPlanError('invalid_cached_plan') from None
            validate_plan(cached.get('plan'),question)
            return {**cached,'question':question,'queries':retrieval_queries(question,cached['plan']),
                    'cache_hit':True,'network_request_sent':False}
        start=time.monotonic()
        response=self.client.respond(json.dumps({'user_question':question},ensure_ascii=False),
                                     instructions=self.prompt,max_output_tokens=4096)
        try:data=json.loads(response.text)
        except ValueError:raise SemanticPlanError('invalid_plan_json') from None
        plan=validate_plan(data,question)
        result={'question':question,'plan':plan,'queries':retrieval_queries(question,plan),
                'schema_validated':True,'semantic_review':'pending',
                'model':response.model,'usage':response.usage,
                'elapsed_seconds':round(time.monotonic()-start,2),
                'cache_hit':False,'network_request_sent':True,
                'prompt_sha256':hashlib.sha256(self.prompt.encode()).hexdigest()}
        self.cache_dir.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        return result
