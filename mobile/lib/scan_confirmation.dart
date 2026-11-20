import 'app_language.dart';
import 'package:flutter/material.dart';
import 'external_links.dart';

Future<void> showScanConfirmation(BuildContext context,String shop,Map result) => showModalBottomSheet<void>(
 context:context,useSafeArea:true,showDragHandle:true,isScrollControlled:true,
 builder:(_)=>ScanConfirmation(shop:shop,result:result),
);
class ScanConfirmation extends StatefulWidget {
 final String shop;final Map result;
 const ScanConfirmation({super.key,required this.shop,required this.result});
 @override State<ScanConfirmation> createState()=>_ScanConfirmationState();
}
class _ScanConfirmationState extends State<ScanConfirmation>{
 bool opening=false;String error='';
 @override Widget build(BuildContext context){
  final welcome=widget.result['status']=='welcome',points=widget.result['points'] as num? ?? 0;
  final facebook=socialLinks(widget.result['facebook_url'])['facebook'];
  return SingleChildScrollView(child:Padding(padding:const EdgeInsets.all(24),child:Column(mainAxisSize:MainAxisSize.min,children:[
   Icon(welcome?Icons.check_circle_outline:Icons.hourglass_top,color:const Color(0xff087f78),size:54),
   const SizedBox(height:12),AppText(widget.shop,style:const TextStyle(fontWeight:FontWeight.w800,fontSize:22)),
   const SizedBox(height:8),AppText(welcome?(points>0?'+$points points de bienvenue crédités':'Carte retrouvée · bonus déjà reçu'):'Scan enregistré · points en attente',textAlign:TextAlign.center,style:const TextStyle(fontSize:18,fontWeight:FontWeight.bold)),
   const SizedBox(height:8),AppText(welcome?(points>0?'Vos points sont disponibles dans votre portefeuille.':'Le bonus de bienvenue est attribué une seule fois par compte et par commerce.'):'Le commerçant doit valider votre achat avant de créditer les points.',textAlign:TextAlign.center),
   if(facebook!=null)FilledButton.icon(onPressed:opening?null:()async{setState(()=>opening=true);try{await openExternal(facebook);}catch(_){if(mounted)setState(()=>error='Facebook n’a pas pu s’ouvrir. Vous pouvez réessayer.');}finally{if(mounted)setState(()=>opening=false);}},icon:const Icon(Icons.open_in_new),label:const AppText('Ouvrir Facebook')),
   if(error.isNotEmpty)AppText(error),TextButton(onPressed:()=>Navigator.pop(context),child:const AppText('Terminé')),
  ])));
 }
}
