"""Source-only installer. Requires a verified, read-only DB backup before applying.
Run inside the server's actual mvp directory. No web assets or QR links are changed.
"""
from pathlib import Path
import argparse,datetime,hashlib,os,sqlite3,shutil,ast

MARKER='install_mobile_support_v060(app,db,payload,merchant,err)'
MODULE='mobile_support_v060.py'
REQUIRED={'shops','subscriptions','users','merchant_sessions','crm_customers','store_scan_requests','storefront_profiles','commerce_audit'}

def prepare(root,source):
    app=(root/'app.py').read_text(encoding='utf-8')
    if MARKER in app:raise RuntimeError('Mobile support already installed; refusing to overwrite')
    candidates=[line for line in app.splitlines(keepends=True) if line.strip().startswith('if __name__')]
    if len(candidates)!=1:raise RuntimeError('Unexpected app.py structure; no changes made')
    marker=candidates[0]
    insertion='from mobile_support_v060 import install as install_mobile_support_v060\n'+MARKER+'\n'
    result=app.replace(marker,insertion+marker,1)
    ast.parse(result);ast.parse(source)
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dry-run',action='store_true');parser.add_argument('--database',type=Path);parser.add_argument('--public-partner',action='append',default=[])
    args=parser.parse_args();root=Path.cwd();source=(Path(__file__).parent/MODULE).read_text(encoding='utf-8')
    if args.public_partner:raise RuntimeError('Configure TUNIBIZ_PUBLIC_PARTNER_SLUGS explicitly in the server environment; no implicit public authorization')
    target=prepare(root,source)
    if args.dry_run:
        print('DRY RUN PASSED: Python syntax and exact app marker checked; no files or database changed')
        return
    if not args.database or not args.database.is_file():raise RuntimeError('Provide --database with the existing production SQLite file; nothing changed')
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup=Path.home()/'tunibiz-backups'/('mobile-v060-'+stamp);backup.mkdir(parents=True,mode=0o700)
    db=sqlite3.connect(args.database.resolve().as_uri()+'?mode=ro',uri=True)
    try:
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not REQUIRED<=tables:raise RuntimeError('Unexpected schema; no source modified')
        dest=sqlite3.connect(backup/'database.sqlite')
        try:
            db.backup(dest)
            if dest.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('Backup integrity failed')
        finally:dest.close()
    finally:db.close()
    shutil.copy2(root/'app.py',backup/'app.py')
    existed=(root/MODULE).exists()
    if existed:shutil.copy2(root/MODULE,backup/MODULE)
    try:
        for path,value in [(root/MODULE,source),(root/'app.py',target)]:
            tmp=path.with_name(path.name+'.mobile-v060.tmp');tmp.write_text(value,encoding='utf-8');tmp.replace(path)
    except Exception:
        shutil.copy2(backup/'app.py',root/'app.py')
        if existed:shutil.copy2(backup/MODULE,root/MODULE)
        else:(root/MODULE).unlink(missing_ok=True)
        raise
    print('INSTALLED: source routes only, no schema migration; backup:',backup)
    print('Reload the web app, then verify GET /api/mobile/capabilities. The website design and /download remain unchanged.')
if __name__=='__main__':main()
