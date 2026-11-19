"""FCM HTTP v1 delivery. Run from a trusted server, never from a public route.
Requires GOOGLE_APPLICATION_CREDENTIALS or another server-side ADC identity.
"""
import argparse
import time
from google.auth import default
from google.auth.transport.requests import AuthorizedSession

PROJECT = 'tunibiz-782f0'
SCOPE = 'https://www.googleapis.com/auth/firebase.messaging'
URL = f'https://fcm.googleapis.com/v1/projects/{PROJECT}/messages:send'

def message(token, scan_id):
    # Generic lock-screen text. Details remain behind authenticated wallet access.
    return {'message': {'token': token,
        'notification': {'title': 'TUNIBIZ', 'body': 'Une nouvelle information est disponible dans votre portefeuille.'},
        'android': {'ttl': '600s', 'notification': {'tag': 'scan-' + scan_id}}}}

def deliver(db, send, limit=20):
    """Bounded batch. Short lease avoids simultaneous sends; delivery is at-least-once."""
    result={'sent':0,'retry':0,'discarded':0}
    for _ in range(min(max(limit,1),50)):
        now=int(time.time())
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            c.execute('DELETE FROM push_outbox WHERE created<=?',(now-600,))
            c.execute('DELETE FROM push_devices WHERE session_digest IN (SELECT digest FROM wallet_sessions WHERE expires<=?)',(now,))
            row=c.execute("""SELECT o.id,o.scan_id,d.token
              FROM push_outbox o JOIN push_devices d ON d.device_id=o.device_id
              JOIN wallet_sessions s ON s.digest=d.session_digest
              JOIN store_scan_requests r ON r.id=o.scan_id AND r.account_id=s.account_id
              WHERE s.expires>? AND o.next_attempt<=? AND o.attempts<5 ORDER BY o.id LIMIT 1""",(now,now)).fetchone()
            if not row:break
            c.execute('UPDATE push_outbox SET attempts=attempts+1,next_attempt=? WHERE id=?',(now+120,row['id']))
            row=dict(row)
        try:
            status=send(message(row['token'],row['scan_id']))
        except Exception:
            status='retry'
        with db() as c:
            if status=='sent':
                c.execute('DELETE FROM push_outbox WHERE id=? AND scan_id=?',(row['id'],row['scan_id']));result['sent']+=1
            elif status=='unregistered':
                c.execute('DELETE FROM push_devices WHERE token=?',(row['token'],));result['discarded']+=1
            else:
                result['retry']+=1
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--send',action='store_true',help='Actually transmit pending notifications')
    args=parser.parse_args()
    if not args.send:
        print('Dry run: no credentials read, no notifications sent.')
        return
    from app import db
    credentials,_=default(scopes=[SCOPE])
    client=AuthorizedSession(credentials)
    def send(body):
        response=client.post(URL,json=body,timeout=10)
        if response.ok:return 'sent'
        if response.status_code==404:
            details=response.json().get('error',{}).get('details',[])
            if any(x.get('errorCode')=='UNREGISTERED' for x in details):return 'unregistered'
        return 'retry'
    try:
        print(deliver(db,send))
    finally:
        client.close()

if __name__=='__main__':main()
