import 'package:flutter/material.dart';
import 'premium.dart';
import 'reward_tile.dart';

String? offerPhoto(Map offer)=>rewardAssets[offer['visual']??offer['category']];
String campaignStatus(Map offer,{DateTime? now}){
 if(offer['active']==0)return 'Arrêtée';
 final day=(now??DateTime.now()).toUtc().add(const Duration(hours:1)).toIso8601String().substring(0,10);
 final start=offer['starts']?.toString()??'',end=offer['ends']?.toString()??'';
 if(end.isNotEmpty&&end.compareTo(day)<0)return 'Terminée';
 if(start.isNotEmpty&&start.compareTo(day)>0)return 'Programmée';
 return 'Active';
}
class OfferArtwork extends StatelessWidget{
 final Map offer;final double height;
 const OfferArtwork({super.key,required this.offer,this.height=146});
 @override Widget build(BuildContext context){
 final asset=offerPhoto(offer);
 return SizedBox(height:height,width:double.infinity,child:Stack(fit:StackFit.expand,children:[
 if(asset!=null)Image.asset(asset,fit:BoxFit.cover)else const DecoratedBox(decoration:BoxDecoration(gradient:LinearGradient(colors:[ink,Color(0xFF196780)])),child:Center(child:Icon(Icons.campaign_outlined,size:54,color:mint))),
 const DecoratedBox(decoration:BoxDecoration(gradient:LinearGradient(begin:Alignment.topCenter,end:Alignment.bottomCenter,colors:[Colors.transparent,Color(0x66071321)]))),
 if(asset!=null)const Positioned(bottom:9,right:12,child:Text('Photo illustrative',style:TextStyle(color:Colors.white,fontSize:10)))
 ]));
 }
}
class BusinessOfferTile extends StatelessWidget{
 final Map offer;final bool merchant;final String? subtitle;final VoidCallback? onStop,onOpen;
 const BusinessOfferTile({super.key,required this.offer,this.merchant=false,this.subtitle,this.onStop,this.onOpen});
 @override Widget build(BuildContext context){
 final status=campaignStatus(offer),desc=(offer['description']??'').toString();
 return Material(color:Colors.white,borderRadius:BorderRadius.circular(22),clipBehavior:Clip.antiAlias,child:InkWell(onTap:onOpen,child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
 Stack(children:[OfferArtwork(offer:offer),if(merchant)Positioned(top:12,left:12,child:DecoratedBox(decoration:BoxDecoration(color:status=='Active'?mint:ink,borderRadius:BorderRadius.circular(20)),child:Padding(padding:const EdgeInsets.symmetric(horizontal:12,vertical:6),child:Text(status,style:TextStyle(color:status=='Active'?ink:Colors.white,fontWeight:FontWeight.w800,fontSize:11))))) ]),
 Padding(padding:const EdgeInsets.all(16),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
 Text(offer['title']?.toString()??'',style:const TextStyle(fontSize:20,fontWeight:FontWeight.w800,color:ink)),
 if(desc.isNotEmpty)...[const SizedBox(height:5),Text(desc,style:const TextStyle(color:muted,height:1.4))],
 const SizedBox(height:10),if(subtitle!=null)Text(subtitle!,style:const TextStyle(color:cobalt,fontWeight:FontWeight.w700,fontSize:12)),
 if(offer['ends']!=null)Text('Jusqu’au '+offer['ends'].toString(),style:const TextStyle(color:muted,fontSize:12)),
 if(onStop!=null&&offer['active']==1)Align(alignment:Alignment.centerRight,child:TextButton.icon(onPressed:onStop,icon:const Icon(Icons.pause_circle_outline),label:const Text('Arrêter')))
 ]))
 ])));
 }
}
Future<String?> chooseOfferVisual(BuildContext context,{bool nearby=false})=>showModalBottomSheet<String>(context:context,showDragHandle:true,isScrollControlled:true,useSafeArea:true,builder:(ctx)=>Padding(padding:const EdgeInsets.all(18),child:Column(mainAxisSize:MainAxisSize.min,crossAxisAlignment:CrossAxisAlignment.stretch,children:[
 const Text('Choisir un visuel',style:TextStyle(fontSize:24,fontWeight:FontWeight.w800,color:ink)),
 const Text('Photos illustratives de la bibliothèque TUNIBIZ.',style:TextStyle(color:muted)),
 const SizedBox(height:12),Flexible(child:GridView.count(shrinkWrap:true,crossAxisCount:2,mainAxisSpacing:10,crossAxisSpacing:10,childAspectRatio:1.25,children:[
 for(final entry in {...rewardVisuals,if(nearby)'beauty':'Beauté et bien-être'}.entries)Material(color:Colors.white,borderRadius:BorderRadius.circular(16),clipBehavior:Clip.antiAlias,child:InkWell(onTap:()=>Navigator.pop(ctx,entry.key),child:Column(children:[Expanded(child:rewardAssets[entry.key]!=null?Image.asset(rewardAssets[entry.key]!,width:double.infinity,fit:BoxFit.cover):const ColoredBox(color:ink,child:Center(child:Icon(Icons.campaign,color:mint,size:34)))),Padding(padding:const EdgeInsets.all(8),child:Text(entry.value,maxLines:2,overflow:TextOverflow.ellipsis,style:const TextStyle(fontSize:12,fontWeight:FontWeight.w700)))])))
 ]))
 ])));
