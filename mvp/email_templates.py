"""Shared transactional layout. No remote tracking images or unescaped user HTML."""
from html import escape
from urllib.parse import quote
from datetime import datetime,timezone

ORIGIN='https://ihebhaouech.pythonanywhere.com'
LOGO_CID='tunibiz-logo@brand.tunibiz'

def layout(title,body,*,preheader='',action=None,link=None,note=''):
 title=escape(title)
 paragraphs=''.join('<p style="margin:0 0 16px;color:#334155;font-size:16px;line-height:1.65">'+escape(line)+'</p>' for line in body.split('\n\n') if line)
 cta=''
 if action and link:
  url=escape(link,quote=True)
  cta=f'''<table role="presentation" cellspacing="0" cellpadding="0" style="margin:24px auto"><tr><td bgcolor="#2563EB" style="border-radius:10px"><a href="{url}" style="display:inline-block;padding:16px 24px;color:#ffffff;text-decoration:none;font-size:16px;font-weight:bold">{escape(action)}</a></td></tr></table>
  <p style="font-size:12px;color:#475569;line-height:1.6">Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :<br><a href="{url}" style="color:#1D4ED8;overflow-wrap:anywhere;word-break:break-all">{url}</a></p>'''
 security=f'<p style="margin:0;padding:16px;background:#F1F5F9;border-radius:10px;font-size:13px;color:#334155;line-height:1.6">{escape(note)}</p>' if note else ''
 year=datetime.now(timezone.utc).year
 return f'''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title></head>
 <body style="margin:0;padding:0;background:#F1F5F9;color:#091628;font-family:Arial,Helvetica,sans-serif">
 <div style="display:none;max-height:0;overflow:hidden;opacity:0;mso-hide:all">{escape(preheader)}</div>
 <table role="presentation" width="100%" cellspacing="0" cellpadding="0" bgcolor="#F1F5F9"><tr><td align="center" style="padding:24px 12px">
 <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:600px">
 <tr><td bgcolor="#091628" style="padding:26px 24px;color:#ffffff;border-radius:18px 18px 0 0">
 <table role="presentation" cellspacing="0" cellpadding="0"><tr><td width="62"><img src="cid:{LOGO_CID}" width="48" height="48" alt="Logo TUNIBIZ" style="display:block;border:0;border-radius:11px"></td><td><span style="font-size:25px;font-weight:bold;color:#ffffff;letter-spacing:1px">TUNIBIZ</span><br><span style="font-size:12px;color:#BFEDE6">Vos commerces. Vos avantages.</span></td></tr></table></td></tr>
 <tr><td bgcolor="#2DD4BF" height="4" style="font-size:0;line-height:0">&nbsp;</td></tr>
 <tr><td bgcolor="#ffffff" style="padding:32px 24px;border-radius:0 0 18px 18px">
 <p style="margin:0 0 12px;color:#1D4ED8;font-weight:bold;font-size:11px;letter-spacing:1.5px">ESPACE TUNIBIZ</p><h1 style="margin:0 0 22px;font-size:27px;line-height:1.25;color:#091628">{title}</h1>
 {paragraphs}{cta}{security}
 <p style="margin:25px 0 0;color:#091628;font-size:15px;line-height:1.6">À bientôt,<br><strong>L'équipe TUNIBIZ</strong></p></td></tr>
 <tr><td align="center" style="padding:20px 12px;color:#475569;font-size:12px;line-height:1.7">Message automatique relatif à votre compte.<br><a href="{ORIGIN}/" style="color:#1D4ED8">Site TUNIBIZ</a><br>© {year} TUNIBIZ · Tunisie</td></tr>
 </table></td></tr></table></body></html>'''

def transactional(title,body,*,preheader,action,link,note):
 text=body+'\n\n'+action+' :\n'+link+'\n\n'+note+"\n\nL'équipe TUNIBIZ"
 return text,layout(title,body,preheader=preheader,action=action,link=link,note=note)

def verification(token):
 link=ORIGIN+'/verify-email#'+quote(token,safe='')
 return ('Bienvenue sur TUNIBIZ — confirmez votre adresse email',*transactional(
 'Confirmez votre adresse email',
 'Bonjour,\n\nBienvenue sur TUNIBIZ ! Retrouvez vos commerces préférés, découvrez leurs offres et cumulez vos points de fidélité.\n\nPour sécuriser votre compte et accéder à la fidélité, confirmez votre adresse email.',
 preheader='Une dernière étape pour profiter de votre compte.',
 action='Confirmer mon adresse email',link=link,
 note="Ce lien est valable 20 minutes et ne peut être utilisé qu'une seule fois. Si vous n'avez pas créé ce compte, ignorez ce message."))

def password_reset(token):
 link=ORIGIN+'/reset-password#'+quote(token,safe='')
 return ('TUNIBIZ — réinitialisation de votre mot de passe',*transactional(
 'Réinitialisez votre mot de passe',
 'Bonjour,\n\nNous avons reçu une demande de réinitialisation du mot de passe de votre compte TUNIBIZ.\n\nChoisissez un nouveau mot de passe sécurisé en cliquant sur le bouton ci-dessous.',
 preheader='Retrouvez votre accès en toute sécurité.',
 action='Choisir un nouveau mot de passe',link=link,
 note="Ce lien est valable 20 minutes et ne peut être utilisé qu'une seule fois. Si vous n'avez pas demandé cette réinitialisation, ignorez ce message. Votre mot de passe reste inchangé."))
