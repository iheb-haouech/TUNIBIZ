from pathlib import Path
import requests,io
from PIL import Image,ImageOps
from concurrent.futures import ThreadPoolExecutor
p=Path(__file__).parent/'static'; a=p/'media';a.mkdir(exist_ok=True)
items={'hero':36729734,'restaurant':5490830,'cafe':8441251}
def fetch(v):
 name,id=v
 u=f'https://images.pexels.com/photos/{id}/pexels-photo-{id}.jpeg?auto=compress&cs=tinysrgb&w=1400'
 r=requests.get(u,timeout=20);r.raise_for_status()
 im=Image.open(io.BytesIO(r.content)).convert('RGB');im.thumbnail((1400,1000));im.save(a/(name+'.webp'),'WEBP',quality=83)
 print(name,im.size,flush=True)
with ThreadPoolExecutor(max_workers=3) as e:list(e.map(fetch,items.items()))
(a/'CREDITS.md').write_text('Illustrative stock photographs (not actual TUNIBIZ customers): Pexels license https://www.pexels.com/license/\\n- Vitaly Gariev, 36729734\\n- Rachel Claire, 5490830\\n- Ron Lach, 8441251\\n',encoding='utf-8')
