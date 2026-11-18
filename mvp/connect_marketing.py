from pathlib import Path
p=Path(__file__).parent/'static'/'index.html'
s=p.read_text(encoding='utf-8')
s=s.replace('<link rel="icon" href="/static/icon.svg">','<link rel="icon" href="/static/icon.svg"><meta name="description" content="TUNIBIZ : menu digital, commandes, réservations et suivi des ventes pour les commerces tunisiens. Découvrez le prototype."><link rel="stylesheet" href="/static/marketing.css">')
s=s.replace('<script src="/static/app.js"></script>','<noscript>Activez JavaScript pour accéder au prototype TUNIBIZ.</noscript><script>const entry=document.createElement("script");entry.src=location.pathname==="/" ? "/static/marketing.js?v=2" : "/static/app.js";document.body.appendChild(entry);</script>')
assert 'marketing.js?v=2' in s
p.write_text(s,encoding='utf-8')
print('MARKETING CONNECTED')
