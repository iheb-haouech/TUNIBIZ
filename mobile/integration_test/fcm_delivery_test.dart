// Real FCM sender runs on the owner's server; only isolated TEST accounts are used.
import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:tunibiz_mobile/api.dart';
import 'package:tunibiz_mobile/session_vault.dart';
import 'package:tunibiz_mobile/loyalty_notifications.dart';

void main(){
 final binding=IntegrationTestWidgetsFlutterBinding.ensureInitialized();
 testWidgets('real FCM foreground refresh and Android background notification',(tester)async{
  const qa='http://10.0.2.2:8879',root='/data/user/0/tn.tunibiz.tunibiz_mobile/cache/qa';
  final client=Api(scope:'wallet',serverUrl:qa),merchant=Api(serverUrl:qa);
  final run=DateTime.now().microsecondsSinceEpoch.toString();
  Future<void> stage(String phase,[String value=''])async{
   await File('$root/qa-fcm-stage').parent.create(recursive:true);
   await File('$root/qa-fcm-stage').writeAsString(jsonEncode({'run':run,'phase':phase,'value':value}));
   for(var i=0;i<180;i++){
    final ack=File('$root/qa-fcm-$run-$phase-ack');
    if(await File('${ack.path}.failed').exists())throw TestFailure('Android did not confirm FCM phase: $phase');
    if(await ack.exists())return;
    await Future<void>.delayed(const Duration(milliseconds:250));
   }
   throw TestFailure('Host did not confirm FCM phase: $phase');
  }
  Future<Map> send(String token,String phase,int id)async{
   final http=HttpClient();try{
    final req=await http.postUrl(Uri.parse('http://10.0.2.2:8880/send'));
    req.headers.contentType=ContentType.json;req.write(jsonEncode({'token':token,'run':run,'phase':phase,'notice_id':id}));
    final res=await req.close().timeout(const Duration(seconds:75));
    final data=jsonDecode(await utf8.decoder.bind(res).join()) as Map;
    expect(res.statusCode,200,reason:data['error']?.toString());expect(data['accepted'],true);return data;
   }finally{http.close();}
  }
  try{
   await tester.pumpWidget(const MaterialApp(home:Scaffold(body:Center(child:Text('TUNIBIZ — vérification FCM réelle')))));
   await SessionVault.write('analytics','no');await SessionVault.write('push_consent','yes');
   await client.init();await client.call('/wallet/login',{'email':'client.qa@example.test','password':'QA-Client-060!'});
   await merchant.init();await merchant.call('/login',{'email':'merchant.qa@example.test','password':'QA-Merchant-060!'});
   await Firebase.initializeApp();final messaging=FirebaseMessaging.instance;
   await messaging.requestPermission();await messaging.setAutoInitEnabled(true);
   final token=await messaging.getToken();expect(token,isNotNull);
   var refreshes=0;
   await LoyaltyNotifications.start(client,()async{await client.call('/wallet');refreshes++;});
   final card=((await client.call('/wallet'))['cards'] as List).firstWhere((r)=>r['shop_id']==4);
   await merchant.call('/commerce/points',{'id':card['id'],'points':1,'reason':'Recette FCM réelle TEST','key':'fcm-$run'});
   final profile=await client.call('/commerce/profile');final id=(profile['notifications'] as List).first['id'] as int;
   final received=FirebaseMessaging.onMessage.firstWhere((m)=>m.data['qa_run']==run).timeout(const Duration(seconds:60));
   final provider=await send(token!,'foreground',id);await received;
   for(var i=0;i<120&&refreshes==0;i++){await tester.pump(const Duration(milliseconds:250));}
   expect(refreshes,greaterThan(0));
   int hash=0;for(final u in 'notice:$id'.codeUnits){hash=((31*hash)+u)&0xffffffff;}if(hash>=0x80000000)hash-=0x100000000;
   await stage('foreground',hash.toString());
   binding.reportData={'foreground_sdk_received':true,'authenticated_refresh':true,'foreground_native_notification':true,'provider_accepted':provider['accepted'],'real_fcm_delivery':true,'production_customer_writes':false};
   await stage('background');
   await send(token,'background',id);await stage('inspect_background');
   binding.reportData!['background_android_notification']=true;
   await client.call('/push/unregister',{'device_id':await SessionVault.read('push_device')});
   await LoyaltyNotifications.stop();await messaging.setAutoInitEnabled(false);await messaging.deleteToken();
  }finally{await LoyaltyNotifications.stop();await SessionVault.write('push_consent',null);client.close();merchant.close();}
 });
}
