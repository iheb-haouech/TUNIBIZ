import requests, re, datetime, sqlite3, uuid
from pathlib import Path
P=Path(__file__).parent;url='http://127.0.0.1:8877'; a=requests.Session();b=requests.Session()
def auth(s):return {'X-CSRF-Token':s.get(url+'/api/session').json()['csrf']}
ah=auth(a);bh=auth(b); ids=[]; rid=None; campaigns=[]
def post(s,h,p,d,status=200):r=s.post(url+'/api'+p,json=d,headers=h);assert r.status_code==status,(p,r.status_code,r.text);return r.json()
def get(s,p):r=s.get(url+'/api'+p);r.raise_for_status();return r.json()
def ck(t,x):assert x,t;print('PASS',t,flush=True)
try:
 ck('CRM requires login',b.get(url+'/api/crm').status_code==401)
 pw=re.search(r'Mot de passe: (.+)',(P/'data/demo-login.txt').read_text(encoding='utf-8')).group(1).strip()
 post(a,ah,'/login',{'email':'demo@tunibiz.local','password':pw})
 for consent in [True,False]:
  r=post(a,ah,'/crm/customer',{'name':'QA CRM '+str(uuid.uuid4())[:8],'phone':'','consent':consent},201);ids.append(r['id'])
  if consent: code=r['code']
 ck('personal codes and client creation',len(ids)==2 and len(code)>20)
 k=str(uuid.uuid4())
 post(a,ah,'/crm/purchase',{'id':ids[0],'amount':120500,'label':'QA purchase','key':k},201)
 ck('idempotent purchase',post(a,ah,'/crm/purchase',{'id':ids[0],'amount':120500,'label':'QA purchase','key':k})['duplicate'])
 d=get(a,'/crm/customer/'+str(ids[0]));ck('points and purchase history',d['customer']['points']==120 and d['customer']['spent']==120500 and len(d['history'])==1)
 rid=post(a,ah,'/crm/reward',{'title':'QA reward','cost':100},201)['id']
 day=datetime.date.today().isoformat(); campaigns.append(post(a,ah,'/crm/campaign',{'title':'QA VIP','description':'QA offer','segment':'vip','starts':day,'ends':day},201)['id'])
 campaigns.append(post(a,ah,'/crm/campaign',{'title':'QA inactive','description':'QA offer','segment':'inactive','starts':day,'ends':day},201)['id'])
 ck('private card requires code',b.get(url+'/api/loyalty').status_code==401)
 post(b,bh,'/loyalty/login',{'code':code});d=get(b,'/loyalty')
 ck('VIP campaign visible; inactive excluded',campaigns[0] in [x['id'] for x in d['campaigns']] and campaigns[1] not in [x['id'] for x in d['campaigns']])
 ck('private card excludes phone and code','phone' not in d['customer'] and 'code_hash' not in d['customer'])
 post(a,ah,'/crm/redeem',{'id':ids[0],'reward':rid,'key':str(uuid.uuid4())},201)
 ck('reward debits points',get(b,'/loyalty')['customer']['points']==20)
 post(a,ah,'/crm/redeem',{'id':ids[0],'reward':rid,'key':str(uuid.uuid4())},400)
 post(b,bh,'/loyalty/optout',{})
 ck('consent withdrawal hides marketing',not get(b,'/loyalty')['campaigns'])
 post(a,ah,'/crm/customer/reset',{'id':ids[0]})
 ck('revoked card session invalid',b.get(url+'/api/loyalty').status_code==401)
 print('CRM TESTS PASSED')
finally:
 with sqlite3.connect(P/'data/tunibiz.sqlite') as c:
  for i in ids:c.execute('DELETE FROM loyalty_ledger WHERE customer_id=?',(i,));c.execute('DELETE FROM crm_customers WHERE id=?',(i,))
  if rid:c.execute('DELETE FROM rewards WHERE id=?',(rid,))
  for i in campaigns:c.execute('DELETE FROM campaigns WHERE id=?',(i,))
