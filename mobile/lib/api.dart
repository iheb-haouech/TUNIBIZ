import 'dart:convert';
import 'dart:io';

const baseUrl=String.fromEnvironment('API_BASE',defaultValue:'http://10.0.2.2:8877');
class Api {
 final HttpClient client=HttpClient()..connectionTimeout=const Duration(seconds:10);
 final Map<String,Cookie> cookies={};
 String csrf='';
 Future<Map<String,dynamic>> call(String path,[Map<String,dynamic>? body]) async {
  final req=await client.openUrl(body==null?'GET':'POST',Uri.parse(baseUrl+'/api'+path));
  req.cookies.addAll(cookies.values);
  if(body!=null){req.headers.contentType=ContentType.json;req.headers.set('X-CSRF-Token',csrf);req.write(jsonEncode(body));}
  final res=await req.close().timeout(const Duration(seconds:15));
  for(final c in res.cookies){if(c.maxAge==0){cookies.remove(c.name);}else{cookies[c.name]=c;}}
  final decoded=jsonDecode(await res.transform(utf8.decoder).join()) as Map<String,dynamic>;
  if(res.statusCode>=400)throw Exception(decoded['error']??'Erreur serveur');
  return decoded;
 }
 Future<void> init() async{csrf=(await call('/session'))['csrf'] as String;}
 void close()=>client.close(force:true);
}
