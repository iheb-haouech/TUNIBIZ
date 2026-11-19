"""Helpers explicitly invoked by isolated regression fixtures; never at startup."""
def publish_fixture(db,sid,photo=None):
 import io,secrets
 from PIL import Image,ImageDraw
 with db() as c:
  if photo is None:
   im=Image.new('RGB',(480,320),'#1e4568');ImageDraw.Draw(im).text((35,130),'QA TEST STORE',fill='white');buf=io.BytesIO();im.save(buf,'JPEG')
   photo=secrets.token_hex(16);c.execute('INSERT INTO storefront_photos VALUES(?,?,?)',(photo,sid,buf.getvalue()))
  c.execute("INSERT INTO storefront_profiles(shop_id,photo,phone,published) VALUES(?,?,'+21620111222',1) ON CONFLICT(shop_id) DO UPDATE SET photo=excluded.photo,phone=excluded.phone,published=1",(sid,photo))
  c.execute("INSERT INTO nearby_locations(shop_id,lat,lon,address,location_confirmed) VALUES(?,33.88,10.86,'QA TEST ADDRESS',1) ON CONFLICT(shop_id) DO NOTHING",(sid,))
 return photo
