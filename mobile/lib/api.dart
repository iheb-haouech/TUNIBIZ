import 'dart:convert';
import 'dart:async';
import 'usage_analytics.dart';
import 'dart:io';
import 'package:flutter/foundation.dart';

const baseUrl=String.fromEnvironment('API_BASE',defaultValue:'http://10.0.2.2:8877');
class Api {
 final HttpClient client=HttpClient()..connectionTimeout=const Duration(seconds:10);
 final Map<String,Cookie> cookies={};
 String csrf='';
 Future<Map<String,dynamic>> call(String path,[Map<String,dynamic>? body]) async {
  if(kReleaseMode && (!baseUrl.startsWith('https://')||Uri.tryParse(baseUrl)?.host.isEmpty!=false))throw StateError('Serveur HTTPS de production non configure');
 final req=await client.openUrl(body==null?'GET':'POST',Uri.parse(baseUrl+'/api'+path));
  req.followRedirects=false;
 if(UsageAnalytics.allowed){req.headers.set('X-Tunibiz-Analytics','yes');req.headers.set('X-Tunibiz-Platform','android');}
 req.cookies.addAll(cookies.values);
  if(body!=null){req.headers.contentType=ContentType.json;req.headers.set('X-CSRF-Token',csrf);req.write(jsonEncode(body));}
  final res=await req.close().timeout(const Duration(seconds:15));
  for(final c in res.cookies){if(c.maxAge==0){cookies.remove(c.name);}else{cookies[c.name]=c;}}
  if(res.statusCode>=300&&res.statusCode<400){await res.drain();throw Exception('Redirection serveur refusée');}
 final decoded=jsonDecode(await res.transform(utf8.decoder).join()) as Map<String,dynamic>;
  if(res.statusCode>=400)throw Exception(decoded['error']??'Erreur serveur');
  final event=res.headers.value('X-Tunibiz-Event');if(event!=null)unawaited(UsageAnalytics.log(event));
  return decoded;
 }
 Future<void> init() async{csrf=(await call('/session'))['csrf'] as String;}
 static Future<void> usage(String event)async{
 if(!UsageAnalytics.allowed)return;final a=Api();
 try{await a.init();if(!UsageAnalytics.allowed)return;await a.call('/analytics/event',{'event':event});await UsageAnalytics.log(event);}catch(_){}finally{a.close();}
 }
 void close()=>client.close(force:true);
}
