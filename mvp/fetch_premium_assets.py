from pathlib import Path
import requests,io
from PIL import Image,ImageOps
from concurrent.futures import ThreadPoolExecutor
a=Path(__file__).parent/'static'/'media'
items={'espresso':36871072,'croissant':3892469,'lemonade':5947064,'boutique':5418897}
def fetch(v):
 name,id=v
 u=f'https://images.pexels.com/photos/{id}/pexels-photo-{id}.jpeg?auto=compress&cs=tinysrgb&w=1000'
 r=requests.get(u,timeout=20);r.raise_for_status()
 im=Image.open(io.BytesIO(r.content)).convert('RGB')
 im=ImageOps.fit(im,(720,500) if name=='boutique' else (480,360),method=Image.Resampling.LANCZOS)
 im.save(a/(name+'.webp'),'WEBP',quality=85)
 print('READY',name,im.size,flush=True)
with ThreadPoolExecutor(max_workers=4) as e:list(e.map(fetch,items.items()))
with (a/'CREDITS.md').open('a',encoding='utf-8') as f:
 f.write('\nAdditional illustrative imagery (Pexels License https://www.pexels.com/license/):\n'+'\n'.join(f'- {n}: https://www.pexels.com/photo/{i}/' for n,i in items.items())+'\n')
