"""Stage 1: selected-topic context reaches planning in both UI paths."""
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from telecom_rag.chatbot import Chatbot
from telecom_rag.gms import GMSResponse

REPO=Path(__file__).resolve().parents[1]
PLAN={'retrieval_query':'KT 자동납부 계좌 변경 적용 시점','external_queries':['KT 자동납부 변경 적용 시점'],'needs_external':False,'reason':'선택한 상담 업무를 질문과 연결'}

class Recorder:
    def __init__(self,responses):self.responses=list(responses);self.calls=[]
    def respond(self,text,**kwargs):
        self.calls.append({'input':json.loads(text),'instructions':kwargs['instructions']})
        return GMSResponse(json.dumps(self.responses.pop(0),ensure_ascii=False),'test','completed',{})

def make_store():
    topics={
        'pay':{'name':'자동납부 수단 변경','summary':'회선 명의를 유지하고 납부 계좌를 변경하는 상담',
               'scope':'납부수단 변경; 명의변경과 구별','service_types':['모바일'],
               'condition_keys':['기존 납부자','새 예금주'],'evidence_status':'linked_draft',
               'path':'private/local/topic.md','index_text':'unused long embedding text','is_policy_evidence':True},
        'due':{'name':'납부 기준일 변경','summary':'출금 날짜 변경 상담','scope':'납부 날짜',
               'service_types':['모바일'],'condition_keys':['희망 납부일'],'evidence_status':'linked_draft'}}
    store=SimpleNamespace(repo=REPO,topics=topics,parents={})
    store.engine=SimpleNamespace(tokenizer=SimpleNamespace(encode=lambda text,**kw:SimpleNamespace(offsets=[(i,i+1) for i in range(len(text))])))
    store.search_topics=lambda *a,**kw:[{'item_id':'pay'}]
    store.retrieve=lambda query,ids:{'evidence':[],'topic_metadata':[topics[i] for i in ids],'warnings':[]}
    return store

def make_bot(responses):
    client=Recorder(responses)
    ext=SimpleNamespace(search_index=lambda *a:[])
    bot=Chatbot(make_store(),client,ext);bot.config['external_enabled']=False
    return bot,client

class SelectedTopicPlanningTests(unittest.TestCase):
    def test_explicit_topic_disambiguates_short_question_input(self):
        bot,client=make_bot([PLAN])
        state=bot.retrieve_node({'question':'언제부터 적용돼?','history':[],'explicit_ids':['pay'],'external_requested':False})
        payload=client.calls[0]['input']
        self.assertEqual(payload['question'],'언제부터 적용돼?')
        self.assertEqual(payload['selected_topics'][0]['name'],'자동납부 수단 변경')
        self.assertIn('명의변경과 구별',payload['selected_topics'][0]['scope'])
        self.assertEqual(state['choice']['selected_ids'],['pay'])
        self.assertEqual(state['plan'],PLAN)
        self.assertEqual(len(client.calls),1)

    def test_auto_selection_happens_before_planning(self):
        bot,client=make_bot([{'selected_ids':['pay'],'reason':'질문과 대화에서 선택'},PLAN])
        history=[{'role':'user','content':'부모님 계좌에서 제 계좌로 납부만 바꾸고 싶어요.'}]
        state=bot.retrieve_node({'question':'언제부터야?','history':history,'explicit_ids':[],'external_requested':False})
        self.assertIn('catalog',client.calls[0]['input'])
        self.assertEqual(client.calls[1]['input']['selected_topics'][0]['item_id'],'pay')
        self.assertEqual(client.calls[1]['input']['history'],history)
        self.assertEqual(state['choice']['selected_ids'],['pay'])
        self.assertEqual(len(client.calls),2)

    def test_multiple_topics_are_deduplicated(self):
        bot,client=make_bot([PLAN])
        bot.plan_query('둘 다 바꿀래',[],['pay','due','pay'])
        self.assertEqual([x['item_id'] for x in client.calls[0]['input']['selected_topics']],['pay','due'])

    def test_metadata_does_not_become_policy_or_leak_local_paths(self):
        bot,client=make_bot([PLAN]);bot.plan_query('언제부터?',[],['pay'])
        context=client.calls[0]['input']['selected_topics'][0]
        self.assertFalse(context['is_policy_evidence'])
        self.assertNotIn('path',context);self.assertNotIn('index_text',context)
        self.assertEqual(context['condition_keys'],['기존 납부자','새 예금주'])
        self.assertIn('실제 사용자 값이 아니다',client.calls[0]['instructions'])

    def test_empty_topic_list_still_plans_question(self):
        bot,client=make_bot([PLAN]);bot.plan_query('KT 자동납부 방법',[],[])
        self.assertEqual(client.calls[0]['input']['selected_topics'],[])

    def test_unknown_topic_fails_before_model_call(self):
        bot,client=make_bot([])
        with self.assertRaises(ValueError):bot.plan_query('언제부터?',[],['unknown'])
        self.assertEqual(client.calls,[])

    def test_invalid_model_plan_remains_rejected(self):
        bot,client=make_bot([{'answer':'정책 결론'}])
        with self.assertRaises(ValueError):bot.plan_query('언제부터?',[],['pay'])

if __name__=='__main__':unittest.main()
