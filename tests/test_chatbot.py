import unittest
from telecom_rag.chatbot import validate_answer
class AnswerContract(unittest.TestCase):
 def make(self): return {'claims':[{'text':'가능합니다.','inferred':False,'citations':[{'id':'E1','quote':'본인 인증 후 변경 가능합니다'}]}],'follow_up':''}
 def test_quote(self): self.assertEqual(validate_answer(self.make(),{'E1':{'text':'본인 인증 후 변경 가능합니다.'}})['follow_up'],'')
 def test_fabricated(self):
  with self.assertRaises(ValueError): validate_answer(self.make(),{'E1':{'text':'다른 내용'}})
 def test_inference_disclosure(self):
  d=self.make();d['claims'][0]['inferred']=True
  with self.assertRaises(ValueError): validate_answer(d,{'E1':{'text':'본인 인증 후 변경 가능합니다'}})
 def test_missing_citation(self):
  d=self.make();d['claims'][0]['citations']=[]
  with self.assertRaises(ValueError): validate_answer(d,{})
 def test_unknown_id(self):
  with self.assertRaises(ValueError): validate_answer(self.make(),{})
if __name__=='__main__': unittest.main()


class QuoteWhitespaceTests(unittest.TestCase):
 def test_whitespace_returns_original(self):
  from telecom_rag.answer_validation import original_quote
  self.assertEqual(original_quote('KT 본인 인증 후 변경','KT  본인\n인증 후 변경'),'KT  본인\n인증 후 변경')
 def test_words_cannot_change(self):
  from telecom_rag.answer_validation import original_quote
  self.assertIsNone(original_quote('부모 동의 불필요','부모 동의 필요'))
