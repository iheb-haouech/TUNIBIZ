import 'app_language.dart';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'api.dart';
import 'premium.dart';
import 'business_offer.dart';

class BusinessNearby extends StatefulWidget{
 final Api api;final Future<void> Function() onCreate,onLocation;final Future<void> Function(int) onStop;
 const BusinessNearby({super.key,required this.api,required this.onCreate,required this.onLocation,required this.onStop});
 @override State<BusinessNearby> createState()=>_BusinessNearbyState();
}
class _BusinessNearbyState extends State<BusinessNearby>{
 Map<String,dynamic>? data;bool busy=false,roads=false;String error='';
 @override void initState(){super.initState();load();}
 Future<void> load()async{
 if(busy)return;setState(()=>busy=true);
 try{final d=await widget.api.call('/nearby/business');if(mounted)setState((){data=d;error='';});}
 catch(e){if(mounted)setState(()=>error=e.toString());}finally{if(mounted)setState(()=>busy=false);}
 }
 Future<void> action(Future<void> Function() f)async{if(busy)return;setState(()=>busy=true);try{await f();}finally{if(mounted){setState(()=>busy=false);await load();}}}
 @override Widget build(BuildContext context){
 final loc=data?['location'],radius=(data?['radius'] as num?)?.toDouble(),offers=(data?['offers'] as List?)??[];
 final valid=loc is Map&&loc['lat'] is num&&loc['lon'] is num;
 final p=valid?LatLng((loc['lat'] as num).toDouble(),(loc['lon'] as num).toDouble()):null;
 return Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
 Container(padding:const EdgeInsets.all(20),decoration:BoxDecoration(gradient:const LinearGradient(colors:[ink,Color(0xFF16465C)]),borderRadius:BorderRadius.circular(24)),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
 const AppText('TUNIBIZ · MARKETING LOCAL',style:TextStyle(color:mint,letterSpacing:1.6,fontSize:11,fontWeight:FontWeight.w800)),
 const SizedBox(height:12),const AppText('Promotions à proximité',style:TextStyle(color:Colors.white,fontSize:28,fontWeight:FontWeight.w800)),const SizedBox(height:8),const AppText('Attirez les clients proches de votre établissement.',style:TextStyle(color:Colors.white70)),
 const SizedBox(height:16),FilledButton.icon(onPressed:busy?null:()=>action(widget.onCreate),icon:const Icon(Icons.add),label:const AppText('Créer une promotion'))
 ])),const SizedBox(height:14),
 if(busy)const LinearProgressIndicator(),if(error.isNotEmpty)AppText(error,style:const TextStyle(color:Colors.red)),
 if(data!=null)...[
 Container(padding:const EdgeInsets.all(16),decoration:BoxDecoration(color:Colors.white,borderRadius:BorderRadius.circular(22)),child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
 const AppText('Zone de diffusion',style:TextStyle(fontSize:21,fontWeight:FontWeight.w800,color:ink)),
 if(radius!=null)AppText(radius.round().toString()+' m',style:const TextStyle(fontSize:34,color:cobalt,fontWeight:FontWeight.w900)),
 const AppText('Rayon défini par l’administration TUNIBIZ.',style:TextStyle(fontSize:12,color:muted)),
 if(p!=null&&radius!=null)...[const SizedBox(height:12),ClipRRect(borderRadius:BorderRadius.circular(18),child:ColoredBox(color:const Color(0xFFEAF2F5),child:SizedBox(height:220,child:FlutterMap(key:ValueKey(p.toString()),options:MapOptions(initialCenter:p,initialZoom:radius>3000?11:radius>1000?12:14),children:[
 if(roads)TileLayer(urlTemplate:'https://tile.openstreetmap.org/{z}/{x}/{y}.png',userAgentPackageName:'tn.tunibiz.tunibiz_mobile',maxNativeZoom:19),
 CircleLayer(circles:[CircleMarker(point:p,radius:radius,useRadiusInMeter:true,color:mint.withValues(alpha:.22),borderColor:cobalt,borderStrokeWidth:2)]),
 MarkerLayer(markers:[Marker(point:p,width:42,height:42,child:const Icon(Icons.storefront_rounded,color:cobalt,size:36))])
 ])))),AppText(roads?'© OpenStreetMap contributors · openstreetmap.org/copyright':'Radar géographique · rayon par défaut',style:const TextStyle(fontSize:10,color:muted)),TextButton(onPressed:()=>setState(()=>roads=!roads),child:AppText(roads?'Radar seul':'Afficher les rues')),AppText(loc['address'].toString())]else const AppText('Localisation de l’établissement à confirmer.'),
 OutlinedButton.icon(onPressed:busy?null:()=>action(widget.onLocation),icon:const Icon(Icons.place_outlined),label:const AppText('Modifier mon emplacement'))
 ])),const SizedBox(height:20),Row(children:[const Expanded(child:AppText('Mes promotions',style:TextStyle(color:ink,fontSize:24,fontWeight:FontWeight.w800))),IconButton(onPressed:busy?null:load,icon:const Icon(Icons.refresh),tooltip:tr('Actualiser'))]),
 if(offers.isEmpty)const Padding(padding:EdgeInsets.all(12),child:AppText('Aucune promotion publiée.')),
 for(final o in offers)Padding(padding:const EdgeInsets.only(top:12),child:BusinessOfferTile(offer:o,merchant:true,subtitle:'Rayon : '+(o['radius_override']??radius?.round()??'—').toString()+' m',onStop:busy?null:()=>action(()=>widget.onStop(o['id'] as int))))
 ]
 ]);
 }
}
