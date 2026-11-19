"""Make a consistent SQLite snapshot outside the Git repo, with private permissions.
Run on the hosting account: python3.11 mvp/backup_db.py
No data leaves the hosting account. Retention/second encrypted copy are owner tasks.
"""
import os,json,sqlite3,time
from pathlib import Path
def backup(source,folder):
 os.umask(0o077);folder.mkdir(mode=0o700,parents=True,exist_ok=True);folder.chmod(0o700)
 if not source.is_file():raise FileNotFoundError('Database file missing')
 target=folder/('tunibiz-'+time.strftime('%Y%m%d-%H%M%S',time.gmtime())+'-'+str(os.getpid())+'.sqlite')
 fd=os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
 try:
  with sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True,timeout=20) as src:
   with sqlite3.connect(target) as dst:
    src.backup(dst)
    assert dst.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  target.chmod(0o600)
  return target
 except BaseException:
  target.unlink(missing_ok=True);raise
if __name__=='__main__':
 home=Path.home()/'.tunibiz';config=json.loads((home/'config.json').read_text())
 data=Path(config['TUNIBIZ_DATA_DIR'])
 print('Backup verified:',backup(data/'tunibiz.sqlite',home/'backups'))
