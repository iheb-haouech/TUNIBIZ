"""Run each legacy script in its own process and a disposable application copy.
Network/browser scripts are excluded unless explicitly launched against that copy.
"""
import json,os,shutil,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).parent
def main():
 results=[]
 with tempfile.TemporaryDirectory(prefix='tunibiz-pilot-',ignore_cleanup_errors=True) as tmp:
  copy=Path(tmp)/'mvp';copy.mkdir()
  for f in ROOT.glob('*.py'):shutil.copy2(f,copy/f.name)
  shutil.copytree(ROOT/'static',copy/'static')
  tests=[p for p in sorted(copy.glob('test_*.py')) if 'TemporaryDirectory' in p.read_text(encoding='utf-8') and ('playwright' not in p.read_text(encoding='utf-8') or p.name=='test_storefront_pilot.py')]
  env=os.environ.copy()
  for k in list(env):
   if k.startswith('TUNIBIZ_'):env.pop(k)
  # Legacy fixtures focus on other modules. New security test explicitly enables verification.
  env['TUNIBIZ_REQUIRE_EMAIL_VERIFICATION']='0'
  for test in tests:
   started=time.monotonic()
   try:
    r=subprocess.run([sys.executable,str(test)],cwd=copy,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
    record={'test':test.name,'passed':r.returncode==0,'seconds':round(time.monotonic()-started,2),'output':(r.stdout+r.stderr)[-18000:]}
   except subprocess.TimeoutExpired:
    record={'test':test.name,'passed':False,'seconds':180,'output':'TIMEOUT'}
   results.append(record)
   print(('PASS ' if record['passed'] else 'FAIL ')+test.name,flush=True)
   if not record['passed']:print(record['output'],flush=True)
  report={'tests':results,'passed':sum(r['passed'] for r in results),'total':len(results),'scope':'isolated Python scripts, one process each; no live accounts or server'}
  out=Path(sys.argv[1]) if len(sys.argv)>1 else Path(tmp)/'results.json'
  out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
  print(json.dumps({k:v for k,v in report.items() if k!='tests'}),flush=True)
  return 0 if all(r['passed'] for r in results) else 1
if __name__=='__main__':raise SystemExit(main())
