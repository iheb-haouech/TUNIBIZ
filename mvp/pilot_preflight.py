"""Read-only deployment readiness checks. Never print environment values or identities."""
import importlib.metadata as md,json,os,shutil,sqlite3,sys
from pathlib import Path
def checks():
 out={}
 out['production_mode']=os.getenv('TUNIBIZ_ENV')=='production'
 out['long_secret']=len(os.getenv('TUNIBIZ_SECRET',''))>=48
 raw=os.getenv('TUNIBIZ_DATA_DIR','');data=Path(raw)
 out['absolute_data_dir']=bool(raw) and data.is_absolute()
 out['admin_configured']=bool(os.getenv('TUNIBIZ_ADMIN_PASSWORD_HASH'))
 out['email_verification_required']=os.getenv('TUNIBIZ_REQUIRE_EMAIL_VERIFICATION','1')=='1'
 out['email_delivery_configured']=bool(os.getenv('TUNIBIZ_BREVO_KEY') and os.getenv('TUNIBIZ_EMAIL_FROM'))
 out['google_configured']=all(os.getenv(k) for k in ('TUNIBIZ_GOOGLE_CLIENT_ID','TUNIBIZ_GOOGLE_CLIENT_SECRET','TUNIBIZ_GOOGLE_REDIRECT_URI'))
 out['ga4_configured']=bool(os.getenv('TUNIBIZ_GA4_MEASUREMENT_ID'))
 out['free_disk_at_least_250MiB']=shutil.disk_usage(data if data.exists() else Path.cwd()).free>250*1024*1024
 out['database_exists']=out['absolute_data_dir'] and (data/'tunibiz.sqlite').is_file()
 if out['database_exists']:
  with sqlite3.connect((data/'tunibiz.sqlite').resolve().as_uri()+'?mode=ro',uri=True,timeout=10) as c:
   out['integrity_ok']=c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
   out['foreign_keys_ok']=not c.execute('PRAGMA foreign_key_check').fetchall()
 versions={}
 for name in ('Flask','Werkzeug','Pillow','requests','urllib3','certifi','google-auth'):
  try:versions[name]=md.version(name)
  except md.PackageNotFoundError:versions[name]='missing'
 return {'checks':out,'versions':versions,'note':'Configuration presence is not a real email/Google/Android test; FCM push still requires implementation and device validation.'}
if __name__=='__main__':
 result=checks();print(json.dumps(result,indent=2))
 raise SystemExit(0 if all(result['checks'].values()) else 1)
