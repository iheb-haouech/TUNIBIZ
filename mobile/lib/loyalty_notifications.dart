import 'dart:async';
import 'dart:math';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/services.dart';
import 'api.dart';
import 'session_vault.dart';
import 'app_language.dart';
import 'notification_sync.dart';

/// Opt-in FCM hints refresh authenticated data; they never credit points locally.
class LoyaltyNotifications {
 static StreamSubscription<RemoteMessage>? _foreground,_opened;
 static StreamSubscription<String>? _tokens;
 static Api? _active,_starting;
 static int _generation=0,_activeEpoch=-1,_startingEpoch=-1;
 static final _shown=<String>{};
 static Future<void> start(Api api,Future<void> Function() refresh)async{
  if(!SessionVault.available||!api.signedIn||await SessionVault.read('push_consent')!='yes')return;
  if(identical(_active,api)&&_activeEpoch==api.sessionEpoch||identical(_starting,api)&&_startingEpoch==api.sessionEpoch)return;
  await stop();final lease=_generation,epoch=api.sessionEpoch;_starting=api;_startingEpoch=epoch;
  Future<bool> allowed()async{final consent=await SessionVault.read('push_consent');return lease==_generation&&api.signedIn&&api.sessionEpoch==epoch&&consent=='yes';}
  try{
   if(Firebase.apps.isEmpty)await Firebase.initializeApp();
   final messaging=FirebaseMessaging.instance;
   if(!await allowed()||(await messaging.getNotificationSettings()).authorizationStatus!=AuthorizationStatus.authorized)return;
   await messaging.setAutoInitEnabled(true);
   var device=await SessionVault.read('push_device');
   if(device==null){final r=Random.secure();device=List.generate(16,(_)=>r.nextInt(256).toRadixString(16).padLeft(2,'0')).join();await SessionVault.write('push_device',device);}
   Future<void> register(String token)async{if(!await allowed())return;await api.call('/push/register',{'device_id':device,'token':token,'consent':true});}
   final token=await messaging.getToken();if(token==null||!await allowed())return;
   await register(token);if(!await allowed())return;
   _active=api;_activeEpoch=epoch;
   final sync=ConfirmedNotificationSync(api:api,refresh:refresh,allowed:allowed,show:notice);
   _tokens=messaging.onTokenRefresh.listen((t)async{try{await register(t);}catch(_){}});
   _foreground=FirebaseMessaging.onMessage.listen((_)=>sync.receive());
   _opened=FirebaseMessaging.onMessageOpenedApp.listen((_)async{if(await allowed())await refresh();});
   if(await messaging.getInitialMessage()!=null&&await allowed())await refresh();
  }catch(_){/* An unavailable service never becomes a successful delivery state. */}
  finally{if(lease==_generation){_starting=null;_startingEpoch=-1;}}
 }
 static Future<void> notice(String id)async{
  if(!SessionVault.available||_shown.contains(id)||await SessionVault.read('push_consent')!='yes')return;
  try{
   final ok=await const MethodChannel('tn.tunibiz/private').invokeMethod<bool>('loyaltyNotice',{'id':id,'title':'TUNIBIZ','body':tr('Une nouvelle information est disponible dans votre portefeuille.')});
   if(ok==true){if(_shown.length>=256)_shown.remove(_shown.first);_shown.add(id);}
  }catch(_){}
 }
 static Future<void> stop()async{
  _generation++;_active=null;_starting=null;_activeEpoch=-1;_startingEpoch=-1;
  await _foreground?.cancel();await _opened?.cancel();await _tokens?.cancel();_foreground=null;_opened=null;_tokens=null;
 }
}
