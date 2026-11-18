import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'premium.dart';
String dt(num n)=>(n/1000).toStringAsFixed(3)+' DT';
class BusinessDashboard extends StatefulWidget{
 final Map<String,dynamic> data;final VoidCallback? onQr,onCustomer,onCampaign,onNearby;
 const BusinessDashboard({super.key,required this.data,this.onQr,this.onCustomer,this.onCampaign,this.onNearby});
 @override State<BusinessDashboard> createState()=>_BusinessDashboardState();
}
class _BusinessDashboardState extends State<BusinessDashboard>{
 int days=7;
 Widget metric(String name,String value,IconData icon)=>Container(padding:const EdgeInsets.all(13),decoration:BoxDecoration(color:Colors.white,borderRadius:BorderRadius.circular(16),border:Border.all(color:const Color(0xFFE4EBF2))),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Icon(icon,color:cobalt,size:22),const SizedBox(height:9),FittedBox(fit:BoxFit.scaleDown,alignment:Alignment.centerLeft,child:Text(value,style:const TextStyle(fontSize:25,fontWeight:FontWeight.w800,color:ink))),Text(name,style:const TextStyle(fontSize:12,color:muted))]));
 @override Widget build(BuildContext context){
 final d=widget.data,stats=d['stats'] as Map,analytics=(d['dashboard'] as Map?)??{},all=(analytics['daily'] as List?)??[],daily=all.skip(math.max(0,all.length-days)).toList();
 final sum=daily.fold<num>(0,(n,r)=>n+(r['amount'] as num)),count=daily.fold<num>(0,(n,r)=>n+(r['purchases'] as num));
 final buyers=(analytics['buyers'] as num?)??0,repeat=(analytics['repeat_buyers'] as num?)??0;
 final consent=(stats['customers'] as num)>0?((stats['consented'] as num)/(stats['customers'] as num)*100).round():0;
 final maxAmount=daily.fold<num>(0,(n,r)=>math.max(n,r['amount'] as num));
 return Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
 Container(padding:const EdgeInsets.all(22),decoration:BoxDecoration(gradient:const LinearGradient(colors:[ink,Color(0xFF174158)]),borderRadius:BorderRadius.circular(22)),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
 const Text('TUNIBIZ BUSINESS',style:TextStyle(color:mint,letterSpacing:2,fontSize:11,fontWeight:FontWeight.w800)),const SizedBox(height:10),Text((analytics['shop'] as Map?)?['name']?.toString()??'Votre commerce',style:const TextStyle(color:Colors.white,fontSize:28,fontWeight:FontWeight.w800)),const SizedBox(height:8),const Text('Pilotez votre relation client.',style:TextStyle(color:Colors.white70)),const SizedBox(height:20),Text(dt(stats['spent'] as num),style:const TextStyle(color:mint,fontSize:34,fontWeight:FontWeight.w800)),const Text('Achats fidélité enregistrés · cumul',style:TextStyle(color:Colors.white70,fontSize:12))
 ])),const SizedBox(height:12),
 Row(children:[Expanded(child:metric('Clients inscrits',stats['customers'].toString(),Icons.people_outline)),const SizedBox(width:10),Expanded(child:metric('Points en circulation',stats['points'].toString(),Icons.stars_outlined))]),
 const SizedBox(height:10),Row(children:[Expanded(child:metric('Consentement marketing',consent.toString()+' %',Icons.verified_user_outlined)),const SizedBox(width:10),Expanded(child:metric('Acheteurs récurrents',buyers>0?(repeat/buyers*100).round().toString()+' %':'—',Icons.repeat))]),
 const SizedBox(height:18),
 Container(padding:const EdgeInsets.all(16),decoration:BoxDecoration(color:Colors.white,borderRadius:BorderRadius.circular(20)),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
 const Text('Activité des achats',style:TextStyle(fontWeight:FontWeight.w800,fontSize:20,color:ink)),
 const SizedBox(height:10),SegmentedButton<int>(segments:const [ButtonSegment(value:7,label:Text('7 jours')),ButtonSegment(value:30,label:Text('30 jours'))],selected:{days},onSelectionChanged:(v)=>setState(()=>days=v.first)),
 const SizedBox(height:12),Text(dt(sum),style:const TextStyle(fontWeight:FontWeight.w800,fontSize:25,color:ink)),Text(count.toString()+' achat(s) · '+(count>0?dt(sum/count):'—')+' panier moyen',style:const TextStyle(fontSize:12,color:muted)),
 const SizedBox(height:12),if(daily.isNotEmpty)SizedBox(height:120,child:Row(crossAxisAlignment:CrossAxisAlignment.end,children:[for(final r in daily)Expanded(child:Padding(padding:const EdgeInsets.symmetric(horizontal:1),child:Tooltip(message:r['day'].toString()+' : '+dt(r['amount'] as num),child:Container(height:maxAmount>0?math.max(2,110*(r['amount'] as num)/maxAmount).toDouble():2,color:(r['amount'] as num)>0?cobalt:const Color(0xFFE5EDF3)))))])),
 if(daily.isNotEmpty)Row(mainAxisAlignment:MainAxisAlignment.spaceBetween,children:[Text(daily.first['day'].toString().substring(5),style:const TextStyle(color:muted,fontSize:11)),Text(daily.last['day'].toString().substring(5),style:const TextStyle(color:muted,fontSize:11))]),
 if(sum==0)const Text('Aucun achat sur cette période.',style:TextStyle(color:muted,fontSize:12)),
 const SizedBox(height:10),const Text('Achats saisis dans TUNIBIZ, hors ventes non enregistrées. Jours de Tunis.',style:TextStyle(fontSize:11,color:muted))
 ])),const SizedBox(height:14),
 Row(children:[Expanded(child:metric('Campagnes actives',analytics['active_campaigns']?.toString()??'0',Icons.campaign_outlined)),const SizedBox(width:10),Expanded(child:metric('Offres Nearby actives',analytics['active_nearby']?.toString()??'0',Icons.radar))]),
 const SizedBox(height:18),const Text('Actions rapides',style:TextStyle(fontWeight:FontWeight.w800,fontSize:22,color:ink)),const SizedBox(height:10),
 FilledButton.icon(onPressed:widget.onQr,icon:const Icon(Icons.qr_code_scanner),label:const Text('Identifier une carte QR')),
 OutlinedButton.icon(onPressed:widget.onCustomer,icon:const Icon(Icons.person_add_alt),label:const Text('Nouveau client')),
 OutlinedButton.icon(onPressed:widget.onCampaign,icon:const Icon(Icons.campaign_outlined),label:const Text('Créer une campagne')),
 OutlinedButton.icon(onPressed:widget.onNearby,icon:const Icon(Icons.radar),label:const Text('Gérer Nearby')),
 const Text('Acheteurs récurrents : au moins deux achats enregistrés parmi les acheteurs historiques. Pas de mesure de chiffre d’affaires total ni de conversion publicitaire.',style:TextStyle(fontSize:11,color:muted))
 ]);
 }
}
