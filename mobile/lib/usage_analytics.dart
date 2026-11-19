import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_analytics/firebase_analytics.dart';
import 'session_vault.dart';

class UsageAnalytics {
 static bool allowed=false,restored=false;
 static FirebaseAnalytics? google;
 static Future<void> restore()async{
  if(restored)return;restored=true;
  final saved=await SessionVault.read('analytics');
  await change(saved=='yes',persist:false);
 }
 static Future<void> change(bool value,{bool persist=true})async{
  allowed=value;
  if(persist)await SessionVault.write('analytics',value?'yes':'no');
  if(!value){
   try{
    await google?.setConsent(analyticsStorageConsentGranted:false,adStorageConsentGranted:false,adUserDataConsentGranted:false,adPersonalizationSignalsConsentGranted:false);
    await google?.setAnalyticsCollectionEnabled(false);
    await google?.resetAnalyticsData();
   }catch(_){}
   return;
  }
  try{
   if(Firebase.apps.isEmpty){
    try{await Firebase.initializeApp();}
    catch(_){
     const appId=String.fromEnvironment('FIREBASE_APP_ID'),apiKey=String.fromEnvironment('FIREBASE_API_KEY'),project=String.fromEnvironment('FIREBASE_PROJECT_ID'),sender=String.fromEnvironment('FIREBASE_SENDER_ID');
     if([appId,apiKey,project,sender].any((value)=>value.isEmpty))return;
     await Firebase.initializeApp(options:const FirebaseOptions(apiKey:apiKey,appId:appId,messagingSenderId:sender,projectId:project,storageBucket:String.fromEnvironment('FIREBASE_STORAGE_BUCKET')));
    }
   }
   google=FirebaseAnalytics.instance;
   await google!.setConsent(analyticsStorageConsentGranted:allowed,adStorageConsentGranted:false,adUserDataConsentGranted:false,adPersonalizationSignalsConsentGranted:false);
   await google!.setAnalyticsCollectionEnabled(allowed);
  }catch(_){}
 }
 static Future<void> log(String event)async{
  if(!allowed||google==null||!RegExp(r'^[a-z_]{1,37}$').hasMatch(event))return;
  try{await google!.logEvent(name:'tn_'+event);}catch(_){}
 }
 static Future<void> screen(String name)async{
  if(!allowed||google==null||!const {'home','stores','scanner','nearby','wallet','business','storefront'}.contains(name))return;
  try{await google!.logScreenView(screenName:name);}catch(_){}
 }
 static Future<bool?> preferences(BuildContext context)async=>showDialog<bool>(context:context,builder:(ctx)=>AlertDialog(
  title:const Text('Statistiques facultatives'),
  content:const Text('Autoriser TUNIBIZ et Google Analytics à mesurer les fonctions utilisées ? Les événements ne contiennent ni email, mot de passe, QR, identifiant de compte ni GPS. La publicité reste désactivée. Vous pouvez modifier ce choix à tout moment et utiliser les services en refusant.'),
  actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('Plus tard')),TextButton(onPressed:()=>Navigator.pop(ctx,false),child:const Text('Refuser')),FilledButton(onPressed:()=>Navigator.pop(ctx,true),child:const Text('Accepter'))]));
}