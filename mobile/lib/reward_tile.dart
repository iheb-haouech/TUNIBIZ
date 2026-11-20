import 'app_language.dart';
import 'package:flutter/material.dart';
import 'premium.dart';

const rewardVisuals=<String,String>{
 'general':'Avantage / réduction',
 'coffee':'Café et boissons chaudes',
 'restaurant':'Restaurant',
 'bakery':'Boulangerie et pâtisserie',
 'drinks':'Boissons fraîches',
 'shopping':'Shopping'
};
const rewardAssets=<String,String>{
 'coffee':'assets/espresso.webp',
 'restaurant':'assets/restaurant.webp',
 'bakery':'assets/croissant.webp',
 'drinks':'assets/lemonade.webp',
 'shopping':'assets/boutique.webp'
};
class RewardTile extends StatelessWidget{
 final Map<String,dynamic> reward;
 final int points;
 const RewardTile({super.key,required this.reward,required this.points});
 @override Widget build(BuildContext context){
  final cost=(reward['cost'] as num).toInt();
  final available=points>=cost;
  final remaining=(cost-points).clamp(0,cost);
  final progress=(points/cost).clamp(0.0,1.0).toDouble();
  final asset=rewardAssets[reward['visual']];
  final desc=(reward['description']??'').toString();
  final reduced=MediaQuery.disableAnimationsOf(context);
  return Material(color:Colors.white,borderRadius:BorderRadius.circular(20),clipBehavior:Clip.antiAlias,child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
   SizedBox(height:142,width:double.infinity,child:Stack(fit:StackFit.expand,children:[
    if(asset!=null)Image.asset(asset,fit:BoxFit.cover)else Container(decoration:const BoxDecoration(gradient:LinearGradient(colors:[ink,Color(0xFF143D50)])),child:const Center(child:Icon(Icons.card_giftcard_rounded,color:mint,size:52))),
    const DecoratedBox(decoration:BoxDecoration(gradient:LinearGradient(begin:Alignment.topCenter,end:Alignment.bottomCenter,colors:[Colors.transparent,Color(0x99071321)]))),
    Positioned(top:12,left:12,child:Container(padding:const EdgeInsets.symmetric(horizontal:10,vertical:7),decoration:BoxDecoration(color:available?mint:ink,borderRadius:BorderRadius.circular(20)),child:AppText(available?'DISPONIBLE':'OBJECTIF',style:TextStyle(color:available?ink:Colors.white,fontSize:11,fontWeight:FontWeight.w800)))),
    Positioned(bottom:12,right:12,child:Container(padding:const EdgeInsets.symmetric(horizontal:10,vertical:7),decoration:BoxDecoration(color:Colors.white,borderRadius:BorderRadius.circular(20)),child:AppText(cost.toString()+' pts',style:const TextStyle(color:ink,fontWeight:FontWeight.w800)))),
    if(asset!=null)const Positioned(bottom:16,left:12,child:AppText('Photo illustrative',style:TextStyle(color:Colors.white,fontSize:10)))
   ])),
   Padding(padding:const EdgeInsets.all(16),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
    AppText(reward['title'].toString(),style:const TextStyle(fontSize:20,fontWeight:FontWeight.w800,color:ink)),
    if(desc.isNotEmpty)...[const SizedBox(height:5),AppText(desc,style:const TextStyle(fontSize:13,color:muted,height:1.4))],
    const SizedBox(height:12),
    Row(children:[Expanded(child:AppText(available?'À demander en caisse':'Encore '+remaining.toString()+' points',style:TextStyle(fontSize:13,fontWeight:FontWeight.w700,color:available?const Color(0xFF087F78):muted))),AppText((progress*100).round().toString()+' %',style:const TextStyle(fontSize:12,color:muted))]),
    const SizedBox(height:9),
    TweenAnimationBuilder<double>(tween:Tween(begin:0,end:progress),duration:reduced?Duration.zero:const Duration(milliseconds:550),curve:Curves.easeOutCubic,builder:(_,v,__)=>ClipRRect(borderRadius:BorderRadius.circular(12),child:LinearProgressIndicator(value:v,minHeight:7,backgroundColor:const Color(0xFFE5EDF3),color:available?const Color(0xFF087F78):cobalt)))
   ]))
  ]));
 }
}
