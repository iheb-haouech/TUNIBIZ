"""Trusted-server worker for the existing transactional outboxes; never bundle its key in Android."""
from pathlib import Path
import fcntl
import json
import os
import signal
import sys
import time
from google.auth import default
from google.auth.transport.requests import AuthorizedSession

def main():
    home=Path.home()
    private=home/'.tunibiz'
    config=json.loads((private/'config.json').read_text())
    if config.get('TUNIBIZ_ENV')!='production':
        raise RuntimeError('Explicit production configuration is required')
    credential=Path(config.get('GOOGLE_APPLICATION_CREDENTIALS',''))
    if not credential.is_file():
        raise RuntimeError('Server FCM identity is not configured')
    identity=json.loads(credential.read_text())
    if identity.get('project_id')!='tunibiz-782f0' or identity.get('type')!='service_account':
        raise RuntimeError('Unexpected Firebase server identity')
    lock=(private/'fcm-v061/worker.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    os.environ.update(config)
    root=home/'TUNIBIZ-v052/mvp'
    sys.path.insert(0,str(root))
    from app import db
    from fcm_dispatch import deliver,deliver_commerce,SCOPE,URL
    credentials,_=default(scopes=[SCOPE])
    client=AuthorizedSession(credentials)
    running=True
    def stop(*_):
        nonlocal running
        running=False
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    def send(body):
        response=client.post(URL,json=body,timeout=10)
        if response.ok:
            return 'sent'
        if response.status_code==404:
            details=response.json().get('error',{}).get('details',[])
            if any(x.get('errorCode')=='UNREGISTERED' for x in details):
                return 'unregistered'
        return 'retry'
    print('TUNIBIZ transactional FCM worker ready',flush=True)
    try:
        while running:
            try:
                result={'scans':deliver(db,send),'commerce':deliver_commerce(db,send)}
                if any(any(v.values()) for v in result.values()):
                    print(json.dumps(result),flush=True)
            except Exception as error:
                print('FCM cycle failed: '+type(error).__name__,flush=True)
            for _ in range(15):
                if not running:
                    break
                time.sleep(1)
    finally:
        client.close()
        lock.close()

if __name__=='__main__':
    main()
