import requests,re,datetime
from pathlib import Path
P=Path(__file__).parent;url='http://127.0.0.1:8877'
s=requests.Session();j=s.get(url+'/api/session').json();h={'X-CSRF-Token':j['csrf']};checks=[]
def ck(name,cond):
 assert cond,name
 checks.append(name);print('PASS',name,flush=True)
def post(p,d):return s.post(url+'/api'+p,json=d,headers=h)
for p in ['/','/business','/menu/demo','/manifest.webmanifest','/sw.js','/static/app.js']:
 ck('HTTP '+p,s.get(url+p).status_code==200)
ck('merchant auth required',s.get(url+'/api/business').status_code==401)
ck('csrf required',s.post(url+'/api/login',json={}).status_code==403)
m=s.get(url+'/api/menu/demo').json();i=m['items'][0]
ck('catalogue loaded',len(m['items'])>=5)
ck('invalid order rejected',post('/menu/demo/order',{'customer':'QA test','cart':[{'id':i['id'],'qty':0}]}).status_code==400)
r=post('/menu/demo/order',{'customer':'QA test - demo','table':'01','cart':[{'id':i['id'],'qty':2}]})
ck('order creation + server price',r.status_code==201 and r.json()['total']==2*i['price']);oid=r.json()['id']
r=post('/menu/demo/reserve',{'customer':'QA test - demo','phone':'00000000','day':str(datetime.date.today()+datetime.timedelta(days=1)),'slot':'15:00','guests':2});ck('reservation created',r.status_code==201);rid=r.json()['id']
pw=re.search(r'Mot de passe: (.+)',(P/'data/demo-login.txt').read_text(encoding='utf-8')).group(1).strip()
ck('merchant login',post('/login',{'email':'demo@tunibiz.local','password':pw}).status_code==200)
b=s.get(url+'/api/business').json();ck('order arrives in merchant dashboard',any(o['id']==oid for o in b['orders']))
for state in ['accepted','completed']:ck('order '+state,post('/business/status',{'kind':'orders','id':oid,'status':state}).status_code==200)
ck('sales updated',s.get(url+'/api/business').json()['stats']['sales']==b['stats']['sales']+2*i['price'])
ck('reservation confirmed',post('/business/status',{'kind':'reservations','id':rid,'status':'confirmed'}).status_code==200)
ck('product created',post('/business/item',{'name':'QA test - demo','category':'Test','price':1234}).status_code==200)
items=s.get(url+'/api/business').json()['items'];iid=next(x['id'] for x in items if x['name']=='QA test - demo')
ck('product hidden',post('/business/item',{'id':iid,'name':'QA test - demo','category':'Test','price':1234,'active':False}).status_code==200 and not any(x['id']==iid for x in s.get(url+'/api/menu/demo').json()['items']))
ck('logout',post('/logout',{}).status_code==200 and s.get(url+'/api/business').status_code==401)
# Remove only the records created by this test, leaving the demo clean.
import sqlite3
with sqlite3.connect(P/'data/tunibiz.sqlite') as c:
 c.execute('DELETE FROM order_lines WHERE order_id=?',(oid,));c.execute('DELETE FROM orders WHERE id=?',(oid,));c.execute('DELETE FROM reservations WHERE id=?',(rid,));c.execute('DELETE FROM items WHERE id=?',(iid,))
(P/'TEST_REPORT.txt').write_text('\n'.join('PASS '+x for x in checks)+'\n',encoding='utf-8')
print('ALL',len(checks),'CHECKS PASSED; test data cleaned',flush=True)
