import json,time,hashlib
from pathlib import Path
from telecom_rag.core import RetrievalStore
from telecom_rag.chatbot import Chatbot
from telecom_rag.gms import GMSClient,GMSClientError
from telecom_rag.settings import GMSSettings

import argparse
parser=argparse.ArgumentParser(description='Run five real GMS baseline/RAG comparisons; consumes API usage.')
parser.add_argument('--output-dir',type=Path)
args=parser.parse_args()
repo=Path(__file__).resolve().parents[1]
out=args.output_dir or repo/'.runtime/evaluation'
out.mkdir(parents=True,exist_ok=True)
cfg=json.loads((repo/'config/retrieval.json').read_text(encoding='utf-8-sig'))
store=RetrievalStore(repo,repo/'.runtime',repo/'.runtime/models',cfg);store.check_index()
client=GMSClient(GMSSettings.load(repo))
class TimedChatbot(Chatbot):
 def _json(self,prompt,*args,**kwargs):
  start=time.monotonic()
  try:return super()._json(prompt,*args,**kwargs)
  finally:self.metrics.append({'stage':prompt,'seconds':round(time.monotonic()-start,3)})
 def retrieve_node(self,state):
  start=time.monotonic()
  try:return super().retrieve_node(state)
  finally:self.metrics.append({'stage':'retrieve_total','seconds':round(time.monotonic()-start,3)})
 def generate_node(self,state):
  start=time.monotonic()
  try:return super().generate_node(state)
  finally:self.metrics.append({'stage':'generate_total','seconds':round(time.monotonic()-start,3)})
bot=TimedChatbot(store,client)
cases=[
 ('original','제 명의 KT 휴대폰 요금이 부모님 계좌에서 나가요. 제 계좌로만 바꿀 때 부모님 동의가 필요한가요? 가족결합도 유지하고 싶어요.',['payment_method_change','family_bundle_maintenance']),
 ('due_date','은행 자동납부 출금일은 며칠 중에 선택할 수 있나요?',['payment_due_date_change']),
 ('other_account','제 명의 KT 휴대폰 요금을 아버지 명의 계좌로 자동납부 변경하려면 어디로 신청하고 어떤 동의 서류가 필요한가요?',['payment_method_change']),
 ('transfer','KT 휴대폰을 가족에게 명의변경하려면 어떤 절차와 구비서류를 확인해야 하나요?',['mobile_ownership_transfer']),
 ('renewal','KT 선택약정 24개월이 끝나면 25% 할인이 자동으로 연장되나요?',['selective_contract_discount'])]
path=out/'KT_6단계_RAG전후_5문항_실측.json'
report={'date':'2026-10-23','model':client.settings.model,'data_fingerprint':store.fingerprint(),'design':'같은 질문, 모델. baseline은 문서 미제공; RAG는 명시 주제 선택. 통계적 독립 성능시험 아님.','prompt_hashes':{n:hashlib.sha256(t.encode()).hexdigest() for n,t in bot.prompts.items()},'cases':[]}
def save():path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
for cid,q,ids in cases:
 row={'id':cid,'question':q,'selected_ids':ids};report['cases'].append(row)
 start=time.monotonic()
 try:
  r=client.respond(q,instructions='KT 고객 문의에 한국어로 답하세요. 참고 문서는 제공되지 않았습니다. 모르는 내용이나 확인되지 않은 내용은 명확히 말하고 출처나 링크를 만들어내지 마세요. 간결하게 답하세요.',max_output_tokens=1800)
  row['without_rag']={'text':r.text,'seconds':round(time.monotonic()-start,2),'usage':r.usage}
 except GMSClientError as e:row['without_rag']={'error':e.code,'http_status':e.status_code}
 save();bot.metrics=[]
 try:row['with_rag']=bot.answer(q,selected_ids=ids)
 except (GMSClientError,ValueError) as e:row['with_rag']={'error':getattr(e,'code',type(e).__name__),'http_status':getattr(e,'status_code',None)}
 row['timings']=bot.metrics;save();print(cid,'saved',row['with_rag'].get('elapsed_seconds',row['with_rag'].get('error')),flush=True)
# Same query repeated to examine actual cache traces and latency; not another independent sample.
bot.metrics=[]
try:report['repeat_original']={'result':bot.answer(cases[0][1],selected_ids=cases[0][2]),'timings':bot.metrics}
except (GMSClientError,ValueError) as e:report['repeat_original']={'error':getattr(e,'code',type(e).__name__)}
save();print('evaluation complete',flush=True)
