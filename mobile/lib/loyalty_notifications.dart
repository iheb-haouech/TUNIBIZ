import 'dart:async';
import 'dart:math';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/services.dart';
import 'api.dart';
import 'session_vault.dart';

/// FCM is opt-in. Incoming messages trigger a server refresh, never local credit.
class LoyaltyNotifications {
 static StreamSubscription<RemoteMessage>? _foreground,_opened;
 static StreamSubscription<String>? _tokens;
 static Api? _active;
 static Future<void> start(Api api,Future<void> Function() refresh)async{
  if(!SessionVault.available||!api.signedIn||await SessionVault.read('push_consent')!='yes')return;
  if(identical(_active,api))return;await stop();
  try{
   if(Firebase.apps.isEmpty)await Firebase.initializeApp();
   final messaging=FirebaseMessaging.instance;
   if((await messaging.getNotificationSettings()).authorizationStatus!=AuthorizationStatus.authorized)return;
   await messaging.setAutoInitEnabled(true);
   var device=await SessionVault.read('push_device');
   if(device==null){final r=Random.secure();device=List.generate(16,(_)=>r.nextInt(256).toRadixString(16).padLeft(2,'0')).join();await SessionVault.write('push_device',device);}
   Future<void> register(String token)async{if(api.signedIn&&await SessionVault.read('push_consent')=='yes')await api.call('/push/register',{'device_id':device,'token':token,'consent':true});}
   final token=await messaging.getToken();if(token!=null)await register(token);_active=api;
   _tokens=messaging.onTokenRefresh.listen((t)async{try{await register(t);}catch(_){}});
   _foreground=FirebaseMessaging.onMessage.listen((m)async{await refresh();await notice(m.messageId??DateTime.now().millisecondsSinceEpoch.toString());});
   _opened=FirebaseMessaging.onMessageOpenedApp.listen((_)=>refresh());
   if(await messaging.getInitialMessage()!=null)await refresh();
  }catch(_){/* Consent remains controlled by PushPreferences; no fabricated delivery state. */}
 }
 static Future<void> notice(String id)async{
  if(!SessionVault.available||await SessionVault.read('push_consent')!='yes')return;
  try{await const MethodChannel('tn.tunibiz/private').invokeMethod('loyaltyNotice',{'id':id,'title':'TUNIBIZ','body':'Votre fidélité a été mise à jour.'});}catch(_){}
 }
 static Future<void> stop()async{await _foreground?.cancel();await _opened?.cancel();await _tokens?.cancel();_foreground=null;_opened=null;_tokens=null;_active=null;}
}
