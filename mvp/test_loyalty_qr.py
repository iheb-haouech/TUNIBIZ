import unittest, tempfile, sqlite3, time, hashlib
from pathlib import Path
from contextlib import contextmanager
from flask import Flask,session,request,jsonify,abort
from loyalty_qr import install
class QRTest(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
  path=Path(self.temp.name)/'db.sqlite'
  @contextmanager
  def db():
   c=sqlite3.connect(path);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON')
   try:
    with c:yield c
   finally:c.close()
  self.db=db
  with db() as c:
   c.executescript("""CREATE TABLE crm_customers(id INTEGER PRIMARY KEY,shop_id INTEGER,name TEXT,code_hash TEXT);
   CREATE TABLE loyalty_ledger(customer_id INTEGER,points INTEGER);
   INSERT INTO crm_customers VALUES(1,1,'Test Client','hash1'),(2,2,'Other','hash2');
   INSERT INTO loyalty_ledger VALUES(1,135);""")
  self.app=Flask(__name__);self.app.secret_key='test-key'
  def merchant():
   if not session.get('shop'):abort(401)
   return session['shop']
  install(self.app,db,lambda:request.get_json() or {},merchant,lambda msg,status=400:(jsonify(error=msg),status))
  self.consumer=self.app.test_client();self.owner=self.app.test_client();self.other=self.app.test_client()
  with self.consumer.session_transaction() as s:s['card']=1;s['card_hash']='hash1'
  with self.owner.session_transaction() as s:s['shop']=1
  with self.other.session_transaction() as s:s['shop']=2
 def tearDown(self):self.temp.cleanup()
 def issue(self):
  r=self.consumer.post('/api/loyalty/qr',json={});self.assertEqual(r.status_code,201);return r.get_json()
 def resolve(self,c,t):return c.post('/api/crm/qr/resolve',json={'token':t})
 def test_matrix_and_one_time_scope(self):
  qr=self.issue();t=qr['token'];self.assertEqual(qr['expires_in'],90);self.assertTrue(len(qr['matrix'])>=29);self.assertEqual(len(qr['matrix']),len(qr['matrix'][0]));self.assertTrue(all(isinstance(v,bool) for row in qr['matrix'] for v in row))
  self.assertEqual(self.resolve(self.other,t).status_code,404)
  r=self.resolve(self.owner,t);self.assertEqual(r.status_code,200);self.assertEqual(r.get_json()['customer'],{'id':1,'name':'Test Client','points':135})
  self.assertEqual(self.resolve(self.owner,t).status_code,404)
  with self.db() as c:self.assertEqual(c.execute('SELECT SUM(points) FROM loyalty_ledger').fetchone()[0],135);self.assertEqual(c.execute('SELECT digest FROM loyalty_scan_tokens').fetchone()[0],hashlib.sha256(t.encode()).hexdigest())
 def test_reissue_expire_revoke(self):
  old=self.issue()['token'];new=self.issue()['token'];self.assertEqual(self.resolve(self.owner,old).status_code,404)
  with self.db() as c:c.execute('UPDATE loyalty_scan_tokens SET expires=?',(int(time.time())-1,))
  self.assertEqual(self.resolve(self.owner,new).status_code,404)
  new=self.issue()['token']
  with self.db() as c:c.execute("UPDATE crm_customers SET code_hash='revoked' WHERE id=1")
  self.assertEqual(self.resolve(self.owner,new).status_code,404);self.assertEqual(self.consumer.post('/api/loyalty/qr',json={}).status_code,401)
 def test_unauthenticated_and_malformed(self):
  c=self.app.test_client();self.assertEqual(c.post('/api/loyalty/qr',json={}).status_code,401);self.assertEqual(self.resolve(c,self.issue()['token']).status_code,401);self.assertEqual(self.resolve(self.owner,'not-a-token').status_code,400)
if __name__=='__main__':unittest.main(verbosity=2)
