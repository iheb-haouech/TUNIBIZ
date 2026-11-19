import base64,json,os,tempfile,unittest
from email import policy
from email.parser import BytesParser
from pathlib import Path
from unittest.mock import patch,MagicMock
import gmail_delivery,password_recovery,verification,email_templates

class GmailTests(unittest.TestCase):
 def test_send_only_configuration_and_message(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'auth.json'
   data=dict(client_id='test',client_secret='fake',refresh_token='fake',token_uri='https://oauth2.googleapis.com/token',scopes=[gmail_delivery.SCOPE])
   p.write_text(json.dumps(data))
   p.chmod(0o600)
   with patch.dict(os.environ,{'TUNIBIZ_GMAIL_CREDENTIALS':str(p),'TUNIBIZ_EMAIL_FROM':'sender@example.test'}):
    self.assertTrue(gmail_delivery.ready())
    with patch.object(gmail_delivery.Credentials,'from_authorized_user_file'),patch.object(gmail_delivery,'AuthorizedSession') as s:
     http=s.return_value.__enter__.return_value
     http.post.return_value.status_code=200
     http.post.return_value.json.return_value={'id':'test'}
     verification.send_confirmation('customer@example.test','sample')
     args,kwargs=http.post.call_args
     self.assertEqual(args[0],'https://gmail.googleapis.com/gmail/v1/users/me/messages/send')
     msg=BytesParser(policy=policy.default).parsebytes(base64.urlsafe_b64decode(kwargs['json']['raw']))
     self.assertEqual(str(msg['To']),'customer@example.test')
     self.assertIn('/verify-email#sample',msg.get_body(preferencelist=('plain',)).get_content())
     self.assertIn('Confirmer mon adresse email',msg.get_body(preferencelist=('html',)).get_content())
     self.assertIn('cid:'+email_templates.LOGO_CID,msg.get_body(preferencelist=('html',)).get_content())
     logos=[part for part in msg.walk() if part.get_content_type()=='image/png']
     self.assertEqual(len(logos),1)
     self.assertEqual(logos[0]['Content-ID'],'<'+email_templates.LOGO_CID+'>')
     self.assertEqual(logos[0].get_payload(decode=True),(Path(gmail_delivery.__file__).parent/'static/icon-192.png').read_bytes())
     self.assertIn('20 minutes',msg.get_body(preferencelist=('plain',)).get_content())
     self.assertIn('20 minutes',msg.get_body(preferencelist=('html',)).get_content())
     self.assertNotIn('<script>',email_templates.layout('<script>','<script>'))
     password_recovery.send_link('customer@example.test','another')
     self.assertIn('/reset-password#another',BytesParser(policy=policy.default).parsebytes(base64.urlsafe_b64decode(http.post.call_args.kwargs['json']['raw'])).get_body(preferencelist=('plain',)).get_content())
     http.post.return_value.status_code=403
     with self.assertRaisesRegex(RuntimeError,'Gmail delivery unavailable'):gmail_delivery.send('customer@example.test','test','test')
    data['scopes'].append('https://mail.google.com/')
    p.write_text(json.dumps(data))
    self.assertFalse(gmail_delivery.ready())
    data['scopes']=[gmail_delivery.SCOPE]
    data['token_uri']='https://example.test/token'
    p.write_text(json.dumps(data))
    self.assertFalse(gmail_delivery.ready())

if __name__=='__main__':unittest.main()
