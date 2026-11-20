import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

String? facebookDestination(dynamic value) {
 if(value is! String || value.length>500 || RegExp(r'[\s<>"\x27\\]').hasMatch(value)) return null;
 final u=Uri.tryParse(value);
 const hosts={'facebook.com','www.facebook.com','m.facebook.com','web.facebook.com','fb.com','www.fb.com','fb.me','www.fb.me'};
 if(u==null || u.scheme!='https' || !hosts.contains(u.host) || u.userInfo.isNotEmpty || u.hasPort || u.path.replaceAll('/','').isEmpty) return null;
 return value;
}

Future<void> showScanConfirmation(BuildContext context,String shop,Map result,{Future<void> Function(String)? openFacebook}) => showModalBottomSheet<void>(
 context:context,useSafeArea:true,showDragHandle:true,
 builder:(_)=>ScanConfirmation(shop:shop,result:result,openFacebook:openFacebook),
);

class ScanConfirmation extends StatefulWidget {
 final String shop; final Map result; final Future<void> Function(String)? openFacebook;
 const ScanConfirmation({super.key,required this.shop,required this.result,this.openFacebook});
 @override State<ScanConfirmation> createState()=>_ScanConfirmationState();
}

class _ScanConfirmationState extends State<ScanConfirmation> {
 Timer? timer; bool opening=false,opened=false; String error='';
 late final target=facebookDestination(widget.result['facebook_url']);
 @override void initState(){super.initState();if(target!=null)timer=Timer(const Duration(seconds:3),visit);}
 @override void dispose(){timer?.cancel();super.dispose();}
 Future<void> visit()async{
  if(!mounted || target==null || opening || opened)return;
  timer?.cancel();setState(()=>opening=true);
  try{
   if(widget.openFacebook!=null){await widget.openFacebook!(target!);}
   else {await const MethodChannel('tn.tunibiz/private').invokeMethod('openFacebook',{'url':target});}
   if(mounted)setState(()=>opened=true);
  }catch(_){if(mounted)setState(()=>error='Facebook n’a pas pu s’ouvrir. Vous pouvez réessayer.');}
  finally{if(mounted)setState(()=>opening=false);}
 }
 @override Widget build(BuildContext context){
  final welcome=widget.result['status']=='welcome',points=widget.result['points'] as num? ?? 0;
  return SingleChildScrollView(child:Padding(padding:const EdgeInsets.all(24),child:Column(mainAxisSize:MainAxisSize.min,children:[
   Icon(welcome?Icons.check_circle_outline:Icons.hourglass_top,color:const Color(0xff087f78),size:54),
   const SizedBox(height:12),Text(widget.shop,style:const TextStyle(fontWeight:FontWeight.w800,fontSize:22)),
   const SizedBox(height:8),Text(welcome?(points>0?'+$points points de bienvenue crédités':'Carte retrouvée · bonus déjà reçu'):'Scan enregistré · points en attente',textAlign:TextAlign.center,style:const TextStyle(fontSize:18,fontWeight:FontWeight.bold)),
   const SizedBox(height:8),Text(welcome?(points>0?'Vos points sont disponibles dans votre portefeuille.':'Le bonus de bienvenue est attribué une seule fois par compte et par commerce.'):'Le commerçant doit valider votre achat avant de créditer les points.',textAlign:TextAlign.center),
   if(target!=null)...[const SizedBox(height:16),Text(opened?'Page Facebook ouverte.':error.isNotEmpty?error:'Ouverture de la page Facebook dans 3 secondes…',textAlign:TextAlign.center),
    FilledButton.icon(onPressed:opening?null:(){opened=false;visit();},icon:const Icon(Icons.open_in_new),label:const Text('Ouvrir Facebook'))],
   TextButton(onPressed:()=>Navigator.pop(context),child:Text(target==null?'Terminé':'Rester dans TUNIBIZ')),
  ])));
 }
}
