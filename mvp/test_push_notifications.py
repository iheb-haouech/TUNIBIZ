"""Local regression test; no real FCM tokens or network."""
import hashlib
import sqlite3
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from flask import Flask, jsonify, request
from push_notifications import install
from fcm_dispatch import deliver

def main():
    with tempfile.TemporaryDirectory() as tmp:
        @contextmanager
        def db():
            c=sqlite3.connect(Path(tmp)/'qa.sqlite')
            c.row_factory=sqlite3.Row
            c.execute('PRAGMA foreign_keys=ON')
            try:
                with c: yield c
            finally: c.close()
        digest=lambda s:hashlib.sha256(s.encode()).hexdigest()
        now=int(time.time())
        with db() as c:
            c.executescript("""
            CREATE TABLE wallet_sessions(digest TEXT PRIMARY KEY,account_id INTEGER,expires INTEGER);
            CREATE TABLE store_scan_requests(id TEXT PRIMARY KEY,account_id INTEGER,state TEXT);
            """)
            c.executemany('INSERT INTO wallet_sessions VALUES(?,?,?)',[(digest('a'),1,now+3600),(digest('b'),2,now+3600),(digest('expired'),1,now-10)])
            c.executemany('INSERT INTO store_scan_requests VALUES(?,?,?)',[('scan1',1,'pending'),('scan2',2,'pending'),('scan3',1,'pending')])
        app=Flask(__name__)
        app.secret_key='test-only-not-production'
        install(app,db,lambda:request.get_json() or {},lambda message,status=400:(jsonify(error=message),status),lambda *args:True)
        def client(session_id=None):
            cli=app.test_client()
            if session_id:
                with cli.session_transaction() as s:s['wallet_token']=session_id
            return cli
        a,b,guest,expired=client('a'),client('b'),client(),client('expired')
        device='a'*32
        body={'device_id':device,'token':'fake_a_'+'x'*50,'consent':True}
        assert guest.post('/api/push/register',json=body).status_code==401
        assert expired.post('/api/push/register',json=body).status_code==401
        assert a.post('/api/push/register',json={**body,'consent':False}).status_code==400
        assert a.post('/api/push/register',json=body).status_code==200
        assert a.post('/api/push/register',json=body).status_code==200
        assert b.post('/api/push/register',json={**body,'token':'fake_b_'+'y'*50}).status_code==409
        assert b.post('/api/push/unregister',json={'device_id':device}).status_code==200
        with db() as c:
            assert c.execute('SELECT COUNT(*) FROM push_devices').fetchone()[0]==1
            c.execute("UPDATE store_scan_requests SET state='approved' WHERE id='scan1'")
            c.execute("UPDATE store_scan_requests SET state='approved' WHERE id='scan1'")
            c.execute("UPDATE store_scan_requests SET state='rejected' WHERE id='scan2'")
            assert [r['scan_id'] for r in c.execute('SELECT scan_id FROM push_outbox')]==['scan1']
        calls=[]
        def send(message):
            calls.append(message)
            assert message['message']['token']==body['token']
            return 'retry'
        assert deliver(db,send)=={'sent':0,'retry':1,'discarded':0}
        assert deliver(db,send)=={'sent':0,'retry':0,'discarded':0}
        with db() as c:c.execute('UPDATE push_outbox SET next_attempt=0')
        assert deliver(db,lambda message:'sent')=={'sent':1,'retry':0,'discarded':0}
        assert len(calls)==1
        assert a.post('/api/push/unregister',json={'device_id':device}).status_code==200
        with db() as c:
            assert c.execute('SELECT COUNT(*) FROM push_outbox').fetchone()[0]==0
        assert a.post('/api/push/register',json=body).status_code==200
        with db() as c:
            c.execute("UPDATE store_scan_requests SET state='rejected' WHERE id='scan3'")
            assert c.execute('SELECT COUNT(*) FROM push_outbox').fetchone()[0]==1
            c.execute('DELETE FROM wallet_sessions WHERE digest=?',(digest('a'),))
            assert c.execute('SELECT COUNT(*) FROM push_devices').fetchone()[0]==0
            assert c.execute('SELECT COUNT(*) FROM push_outbox').fetchone()[0]==0
        print('PASS opt-in, authentication, expiry, account isolation, deduplication, opt-out, logout cascade')

if __name__=='__main__':main()
