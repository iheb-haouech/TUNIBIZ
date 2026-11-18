from pathlib import Path
import json
from PIL import Image,ImageDraw
P=Path(__file__).parent;S=P/'static'
svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="25" fill="#2563EB"/><path d="M24 26 H76 V40 H57 V76 H43 V40 H24Z" fill="#fff"/><circle cx="76" cy="76" r="7" fill="#2DD4BF"/></svg>'
(S/'icon.svg').write_text(svg)
for n in [192,512]:
 im=Image.new('RGB',(n,n),'#2563EB');d=ImageDraw.Draw(im);sc=n/100
 d.polygon([(int(x*sc),int(y*sc)) for x,y in [(24,26),(76,26),(76,40),(57,40),(57,76),(43,76),(43,40),(24,40)]],fill='white')
 d.ellipse(tuple(int(x*sc) for x in (69,69,83,83)),fill='#2DD4BF');im.save(S/f'icon-{n}.png')
(S/'manifest.webmanifest').write_text(json.dumps({"name":"TUNIBIZ — Business","short_name":"TUNIBIZ","start_url":"/business","scope":"/","display":"standalone","background_color":"#F6F8FC","theme_color":"#091628","icons":[{"src":f"/static/icon-{n}.png","sizes":f"{n}x{n}","type":"image/png"} for n in (192,512)]}))
(S/'sw.js').write_text("""const CACHE='tunibiz-shell-v1'; self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(['/static/icon.svg','/static/app.js','/static/icon-192.png','/static/icon-512.png'])))); self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('tunibiz-')&&k!==CACHE).map(k=>caches.delete(k)))))); self.addEventListener('fetch',e=>{const u=new URL(e.request.url);if(e.request.method==='GET'&&u.origin===location.origin&&u.pathname.startsWith('/static/'))e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));});""")
(P/'README.md').write_text("""# TUNIBIZ MVP 0.1
Local prototype, France/Tunisie languages: currently French UI only. National Tunisia positioning.
Run: python app.py. URL: http://127.0.0.1:8877. Local demo credentials: data/demo-login.txt.
Local SQLite database, session auth, hashed password, CSRF, server-calculated totals, merchant-scoped queries.
Scope: public web landing, customer menu and cart, reservation requests, merchant catalog/orders/reservations and completed sales.
PWA shell/manifest only; phone access requires HTTPS hosting. No real online payment, loyalty system, real-time notifications, QR public link, multi-merchant registration, admin or APK yet. Do not expose Flask dev server to internet.
""",encoding='utf-8')
print('ASSETS READY')
