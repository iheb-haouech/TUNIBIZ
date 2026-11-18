import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_analytics/firebase_analytics.dart';

class UsageAnalytics{
 static bool allowed=false;
 static FirebaseAnalytics? google;
 static Future<void> change(bool value)async{
  allowed=value;
  if(!value){try{await google?.setAnalyticsCollectionEnabled(false);await google?.resetAnalyticsData();}catch(_){}return;}
  const appId=String.fromEnvironment('FIREBASE_APP_ID'),apiKey=String.fromEnvironment('FIREBASE_API_KEY'),project=String.fromEnvironment('FIREBASE_PROJECT_ID'),sender=String.fromEnvironment('FIREBASE_SENDER_ID');
  if([appId,apiKey,project,sender].any((v)=>v.isEmpty))return;
  try{
   if(Firebase.apps.isEmpty)await Firebase.initializeApp(options:const FirebaseOptions(apiKey:apiKey,appId:appId,messagingSenderId:sender,projectId:project));
   google=FirebaseAnalytics.instance;
   await google!.setConsent(analyticsStorageConsentGranted:allowed,adStorageConsentGranted:false,adUserDataConsentGranted:false,adPersonalizationSignalsConsentGranted:false);
   await google!.setAnalyticsCollectionEnabled(allowed);
  }catch(_){}
 }
 static Future<void> log(String event)async{
  if(!allowed||google==null||!RegExp(r'^[a-z_]{1,40}$').hasMatch(event))return;
  try{await google!.logEvent(name:'tn_'+event);}catch(_){}
 }
 static Future<bool?> preferences(BuildContext context)async=>showDialog<bool>(context:context,builder:(ctx)=>AlertDialog(title:const Text('Statistiques facultatives'),content:const Text('Autoriser TUNIBIZ et, si configuré, Google Analytics à mesurer les fonctions utilisées ? Aucun email, mot de passe, QR, identifiant de compte ni GPS n’est envoyé comme événement. Vos services restent disponibles si vous refusez. Choix valable pendant cette session.'),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('Fermer')),TextButton(onPressed:()=>Navigator.pop(ctx,false),child:const Text('Refuser / désactiver')),FilledButton(onPressed:()=>Navigator.pop(ctx,true),child:const Text('Accepter'))]));
}
