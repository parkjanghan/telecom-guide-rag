import unittest
from telecom_rag.query_expansion import query_plan, fuse_candidates

class QueryExpansionTests(unittest.TestCase):
    def test_preserves_whole_question_and_exact_substrings(self):
        q='인터넷을 이사할 집으로 옮기고 싶어요. 그리고 가족결합은 유지할래요.'
        plan=query_plan(q)
        self.assertEqual(plan[0]['text'],q)
        self.assertGreater(len(plan),1)
        for p in plan:self.assertEqual(q[p['start']:p['end']],p['text'])
    def test_no_split_for_single_intent(self):
        self.assertEqual(len(query_plan('번호이동 신청 방법을 알려주세요')),1)
    def test_negation_is_not_dropped_from_whole_question(self):
        q='명의는 바꾸지 않고 계좌만 변경하고 싶어요.'
        self.assertEqual(query_plan(q)[0]['text'],q)
    def test_candidates_are_unique_and_keep_main_leader(self):
        q=[{'text':'whole'},{'text':'part'}]
        row=lambda id:{'item_id':id,'distance':0.1}
        out=fuse_candidates([[row('a'),row('b')],[row('b'),row('a')]],q,5)
        self.assertEqual([r['item_id'] for r in out],['a','b'])
    def test_query_budget_retains_tail(self):
        q='첫 번째 상담 질문입니다. 두 번째 상담 질문입니다. 세 번째 상담 질문입니다. 네 번째 상담 질문입니다.'
        plan=query_plan(q,max_clauses=2)
        self.assertLessEqual(len(plan),3)
        self.assertTrue(plan[-1]['text'].endswith('네 번째 상담 질문입니다.'))
if __name__=='__main__':unittest.main()
