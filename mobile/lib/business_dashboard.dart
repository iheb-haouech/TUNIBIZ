import 'app_language.dart';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'premium.dart';
import 'business_offer.dart';
import 'merchant_identity.dart';
String dt(num n)=>(n/1000).toStringAsFixed(3)+' DT';
class BusinessDashboard extends StatefulWidget{
 final Map<String,dynamic> data;final VoidCallback? onQr,onCustomer,onCampaign,onNearby,onApprovals,onAnnouncements;
 const BusinessDashboard({super.key,required this.data,this.onQr,this.onCustomer,this.onCampaign,this.onNearby,this.onApprovals,this.onAnnouncements});
 @override State<BusinessDashboard> createState()=>_BusinessDashboardState();
}
class _BusinessDashboardState extends State<BusinessDashboard>{
 int days=7;
 Widget metric(String name,String value,IconData icon)=>Container(padding:const EdgeInsets.all(13),decoration:BoxDecoration(color:Colors.white,borderRadius:BorderRadius.circular(16),border:Border.all(color:const Color(0xFFE4EBF2))),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Icon(icon,color:cobalt,size:22),const SizedBox(height:9),FittedBox(fit:BoxFit.scaleDown,alignment:Alignment.centerLeft,child:AppText(value,style:const TextStyle(fontSize:25,fontWeight:FontWeight.w800,color:ink))),AppText(name,style:const TextStyle(fontSize:12,color:muted))]));
 @override Widget build(BuildContext context){
 final d=widget.data,stats=d['stats'] as Map,analytics=(d['dashboard'] as Map?)??{},all=(analytics['daily'] as List?)??[],daily=all.skip(math.max(0,all.length-days)).toList();
 final sum=daily.fold<num>(0,(n,r)=>n+(r['amount'] as num)),count=daily.fold<num>(0,(n,r)=>n+(r['purchases'] as num));
 final pilot=(analytics['pilot'] as Map?)??{},subscription=analytics['subscription'] as Map?;
 final pricedCount=daily.fold<num>(0,(n,r)=>n+((r['amount_purchases']??r['purchases']) as num));
 final buyers=(analytics['buyers'] as num?)??0,repeat=(analytics['repeat_buyers'] as num?)??0;
 final consent=(stats['customers'] as num)>0?((stats['consented'] as num)/(stats['customers'] as num)*100).round():0;
 final announcements=((d['campaigns'] as List?)??[]).where((o)=>campaignStatus(o)=='Active').take(2).toList();
 final maxAmount=daily.fold<num>(0,(n,r)=>math.max(n,r['amount'] as num));
 return Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
 Container(padding:const EdgeInsets.all(22),decoration:BoxDecoration(gradient:const LinearGradient(colors:[ink,Color(0xFF174158)]),borderRadius:BorderRadius.circular(22)),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
 const AppText('TUNIBIZ BUSINESS',style:TextStyle(color:mint,letterSpacing:2,fontSize:11,fontWeight:FontWeight.w800)),const SizedBox(height:10),AppText((analytics['shop'] as Map?)?['name']?.toString()??'Votre commerce',style:const TextStyle(color:Colors.white,fontSize:28,fontWeight:FontWeight.w800)),const SizedBox(height:8),AppText(establishmentLabel(analytics['shop'] as Map?)+' · '+((analytics['shop'] as Map?)?['city']?.toString()??''),style:const TextStyle(color:Colors.white70)),const SizedBox(height:14),ClipRRect(borderRadius:BorderRadius.circular(14),child:OfferArtwork(offer:{'visual':(analytics['shop'] as Map?)?['category']??'general'},height:116)),const SizedBox(height:16),AppText(dt(stats['spent'] as num),style:const TextStyle(color:mint,fontSize:34,fontWeight:FontWeight.w800)),const AppText('Achats fidélité enregistrés · cumul',style:TextStyle(color:Colors.white70,fontSize:12))
 ])),const SizedBox(height:12),
 if(subscription!=null)Card(child:ListTile(leading:const Icon(Icons.verified_outlined,color:cobalt),title:AppText('Abonnement ${subscription['status']} · 19 DT / mois'),subtitle:AppText('Prochaine échéance : ${subscription['paid_until']} (exclusive)'))),
 if(pilot.isNotEmpty)...[
 Row(children:[Expanded(child:metric('Nouveaux clients · 30 j',pilot['new_customers'].toString(),Icons.person_add_outlined)),const SizedBox(width:10),Expanded(child:metric('Clients actifs · 30 j',pilot['active_customers'].toString(),Icons.people_outline))]),
 const SizedBox(height:10),Row(children:[Expanded(child:metric('Demandes QR en attente',pilot['pending_qr'].toString(),Icons.qr_code)),const SizedBox(width:10),Expanded(child:metric('Points distribués · cumul',pilot['points_issued'].toString(),Icons.stars_outlined))]),
 const SizedBox(height:10),Row(children:[Expanded(child:metric('Coupons obtenus',pilot['coupons_claimed'].toString(),Icons.local_offer_outlined)),const SizedBox(width:10),Expanded(child:metric('Coupons utilisés',pilot['coupons_used'].toString(),Icons.done_all))]),const SizedBox(height:10)],
 Row(children:[Expanded(child:metric('Clients inscrits',stats['customers'].toString(),Icons.people_outline)),const SizedBox(width:10),Expanded(child:metric('Points en circulation',stats['points'].toString(),Icons.stars_outlined))]),
 const SizedBox(height:10),Row(children:[Expanded(child:metric('Consentement marketing',consent.toString()+' %',Icons.verified_user_outlined)),const SizedBox(width:10),Expanded(child:metric('Acheteurs récurrents',buyers>0?(repeat/buyers*100).round().toString()+' %':'—',Icons.repeat))]),
 const SizedBox(height:18),
 Row(children:[Expanded(child:FilledButton.icon(onPressed:widget.onApprovals,icon:const Icon(Icons.qr_code),label:const AppText('Valider QR'))),const SizedBox(width:8),Expanded(child:OutlinedButton.icon(onPressed:widget.onNearby,icon:const Icon(Icons.radar),label:const AppText('Nearby')))]),
 const SizedBox(height:18),
 Row(children:[const Expanded(child:AppText('Annonces',style:TextStyle(fontSize:23,fontWeight:FontWeight.w800,color:ink))),TextButton(onPressed:widget.onAnnouncements,child:const AppText('Tout voir'))]),
 if(announcements.isEmpty)FeatureTile(asset:'assets/restaurant.webp',title:'Créer votre première annonce',subtitle:'Choisissez un visuel et présentez votre offre.',tag:'MARKETING',onTap:widget.onCampaign??(){}),
 for(final o in announcements)Padding(padding:const EdgeInsets.only(top:10),child:BusinessOfferTile(offer:o,merchant:true,onOpen:widget.onAnnouncements)),
 const SizedBox(height:18),
 Container(padding:const EdgeInsets.all(16),decoration:BoxDecoration(color:Colors.white,borderRadius:BorderRadius.circular(20)),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
 const AppText('Activité des achats',style:TextStyle(fontWeight:FontWeight.w800,fontSize:20,color:ink)),
 const SizedBox(height:10),SegmentedButton<int>(segments:const [ButtonSegment(value:7,label:AppText('7 jours')),ButtonSegment(value:30,label:AppText('30 jours'))],selected:{days},onSelectionChanged:(v)=>setState(()=>days=v.first)),
 const SizedBox(height:12),AppText(dt(sum),style:const TextStyle(fontWeight:FontWeight.w800,fontSize:25,color:ink)),AppText(count.toString()+' achat(s) · '+(pricedCount>0?dt(sum/pricedCount)+' panier moyen renseigné':'montants non renseignés'),style:const TextStyle(fontSize:12,color:muted)),
 const SizedBox(height:12),if(daily.isNotEmpty)SizedBox(height:120,child:Row(crossAxisAlignment:CrossAxisAlignment.end,children:[for(final r in daily)Expanded(child:Padding(padding:const EdgeInsets.symmetric(horizontal:1),child:Tooltip(message:r['day'].toString()+' : '+dt(r['amount'] as num),child:Container(height:maxAmount>0?math.max(2,110*(r['amount'] as num)/maxAmount).toDouble():2,color:(r['amount'] as num)>0?cobalt:const Color(0xFFE5EDF3)))))])),
 if(daily.isNotEmpty)Row(mainAxisAlignment:MainAxisAlignment.spaceBetween,children:[AppText(daily.first['day'].toString().substring(5),style:const TextStyle(color:muted,fontSize:11)),AppText(daily.last['day'].toString().substring(5),style:const TextStyle(color:muted,fontSize:11))]),
 if(count==0)const AppText('Aucun achat sur cette période.',style:TextStyle(color:muted,fontSize:12)),
 const SizedBox(height:10),const AppText('Achats saisis dans TUNIBIZ, hors ventes non enregistrées. Jours de Tunis.',style:TextStyle(fontSize:11,color:muted))
 ])),const SizedBox(height:14),
 Row(children:[Expanded(child:metric('Campagnes actives',analytics['active_campaigns']?.toString()??'0',Icons.campaign_outlined)),const SizedBox(width:10),Expanded(child:metric('Offres Nearby actives',analytics['active_nearby']?.toString()??'0',Icons.radar))]),
 const SizedBox(height:18),const AppText('Actions rapides',style:TextStyle(fontWeight:FontWeight.w800,fontSize:22,color:ink)),const SizedBox(height:10),
 FilledButton.icon(onPressed:widget.onQr,icon:const Icon(Icons.qr_code_scanner),label:const AppText('Identifier une carte QR')),
 OutlinedButton.icon(onPressed:widget.onCustomer,icon:const Icon(Icons.person_add_alt),label:const AppText('Nouveau client')),
 OutlinedButton.icon(onPressed:widget.onCampaign,icon:const Icon(Icons.campaign_outlined),label:const AppText('Créer une campagne')),
 OutlinedButton.icon(onPressed:widget.onNearby,icon:const Icon(Icons.radar),label:const AppText('Gérer Nearby')),
 const AppText('Acheteurs récurrents : au moins deux achats enregistrés parmi les acheteurs historiques. Pas de mesure de chiffre d’affaires total ni de conversion publicitaire.',style:TextStyle(fontSize:11,color:muted))
 ]);
 }
}
