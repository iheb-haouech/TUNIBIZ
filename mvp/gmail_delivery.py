"""Transactional mail through the owner's Gmail API, send-only OAuth."""
import base64,json,os
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from email_templates import layout,LOGO_CID
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request,AuthorizedSession
SCOPE='https://www.googleapis.com/auth/gmail.send'

def settings():
 path=os.getenv('TUNIBIZ_GMAIL_CREDENTIALS','')
 sender=os.getenv('TUNIBIZ_EMAIL_FROM','')
 if not path or not sender or not Path(path).is_absolute():
  return None
 try:
  f=Path(path)
  if not f.is_file() or f.stat().st_size>32768:return None
  if os.name!='nt' and f.stat().st_mode&0o077:return None
  config=json.loads(f.read_text(encoding='utf-8'))
  if set(config.get('scopes') or [])!={SCOPE}:return None
  if not all(config.get(k) for k in ('client_id','client_secret','refresh_token')):return None
  if config.get('token_uri')!='https://oauth2.googleapis.com/token':return None
  return f,sender
 except (OSError,ValueError,TypeError):return None

def ready():
 return settings() is not None

def send(email,subject,body,html_body=None):
 cfg=settings()
 if cfg is None:raise RuntimeError('Gmail delivery not configured')
 path,sender=cfg
 message=EmailMessage()
 message['From']=formataddr(('TUNIBIZ',sender))
 message['To']=email
 message['Subject']=subject
 message.set_content(body)
 message.add_alternative(html_body if html_body is not None else layout(subject,body),subtype='html')
 logo=(Path(__file__).resolve().parent/'static'/'icon-192.png').read_bytes()
 message.get_payload()[-1].add_related(logo,maintype='image',subtype='png',cid='<'+LOGO_CID+'>',disposition='inline',filename='tunibiz-logo.png')
 raw=base64.urlsafe_b64encode(message.as_bytes()).decode('ascii')
 try:
  creds=Credentials.from_authorized_user_file(str(path),scopes=[SCOPE])
  with AuthorizedSession(creds,refresh_timeout=8,max_refresh_attempts=1) as session:
   response=session.post('https://gmail.googleapis.com/gmail/v1/users/me/messages/send',json={'raw':raw},timeout=10,max_allowed_time=25,allow_redirects=False)
   if response.status_code!=200:raise RuntimeError('Gmail API refused delivery')
   if not response.json().get('id'):raise RuntimeError('Gmail API did not return a message identifier')
 except Exception:
  raise RuntimeError('Gmail delivery unavailable') from None
