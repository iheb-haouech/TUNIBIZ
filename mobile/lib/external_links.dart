import 'dart:convert';
import 'package:flutter/services.dart';

String? safeWebUrl(Object? value){if(value is! String||value.length>1000||RegExp(r'[\s<>"\x27\\]').hasMatch(value))return null;final u=Uri.tryParse(value);return u!=null&&u.scheme=='https'&&u.host.isNotEmpty&&u.userInfo.isEmpty&&(!u.hasPort||u.port==443)?value:null;}
Map<String,String> socialLinks(Object? raw){
 final result=<String,String>{};if(raw is! String)return result;
 Iterable<String> values;
 try{final json=jsonDecode(raw);values=json is Map?json.values.map((e)=>e.toString()):[raw];}catch(_){values=RegExp(r'https://[^\s<>"\x27]+').allMatches(raw).map((m)=>m.group(0)!);}
 for(final value in values){final url=safeWebUrl(value),u=url==null?null:Uri.tryParse(url);if(u==null)continue;if(const {'facebook.com','www.facebook.com','m.facebook.com','web.facebook.com','fb.com','fb.me'}.contains(u.host)){result['facebook']=url!;}else if(const {'instagram.com','www.instagram.com'}.contains(u.host)){result['instagram']=url!;}}
 return result;
}
Future<void> openExternal(String value)async{
 final phone=value.startsWith('tel:')&&RegExp(r'^tel:\+?[0-9 ()-]{5,30}$').hasMatch(value);
 if(!phone&&safeWebUrl(value)==null)throw const FormatException('Lien HTTPS valide requis.');
 await const MethodChannel('tn.tunibiz/private').invokeMethod('openExternal',{'url':value});
}
