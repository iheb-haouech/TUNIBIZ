import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'api.dart';
import 'premium.dart';

const nearbyCategories={'all':'Tout','general':'Autres','coffee':'Cafés','restaurant':'Restaurants','bakery':'Pâtisseries','drinks':'Boissons','shopping':'Shopping','beauty':'Beauté'};
const nearbyAssets={'coffee':'assets/cafe.webp','restaurant':'assets/restaurant.webp','bakery':'assets/croissant.webp','drinks':'assets/lemonade.webp','shopping':'assets/boutique.webp'};
IconData categoryIcon(String category)=>switch(category){'coffee'=>Icons.coffee,'restaurant'=>Icons.restaurant,'bakery'=>Icons.bakery_dining,'drinks'=>Icons.local_drink,'shopping'=>Icons.shopping_bag_outlined,'beauty'=>Icons.spa_outlined,_=>Icons.local_offer_outlined};
double distanceMeters(double a,double b,double c,double d){
 const r=math.pi/180;
 final h=math.pow(math.sin((c-a)*r/2),2)+math.cos(a*r)*math.cos(c*r)*math.pow(math.sin((d-b)*r/2),2);
 return 12742000*math.asin(math.sqrt(h.clamp(0,1)));
}
List<Map<String,dynamic>> nearbyMatches(List items,LatLng p){
 final out=<Map<String,dynamic>>[];
 for(final raw in items){if(raw is! Map)continue;final a=raw['lat'],b=raw['lon'];if(a is! num||b is! num||!a.isFinite||!b.isFinite||a.abs()>90||b.abs()>180)continue;
 final d=distanceMeters(p.latitude,p.longitude,a.toDouble(),b.toDouble());if(d<=1000){out.add({...Map<String,dynamic>.from(raw),'distance':d});}}
 out.sort((a,b)=>(a['distance'] as double).compareTo(b['distance'] as double));return out;
}
class Nearby extends StatefulWidget{
 const Nearby({super.key,this.apiOverride});
 final Api? apiOverride;
 @override State<Nearby> createState()=>_NearbyState();
}
class _NearbyState extends State<Nearby> with WidgetsBindingObserver{
 late final api=widget.apiOverride??Api();static const channel=MethodChannel('tn.tunibiz/nearby');
 final map=MapController();Timer? timer;bool enabled=false,alerts=false,busy=false,visible=true,baseMap=false,mapReady=false;
 LatLng? position; double? accuracy; int generation=0;
 String category='all',status='Activez la découverte pour voir les offres à moins de 1 km.';
 List<Map<String,dynamic>> matches=[];
 List<Map<String,dynamic>> get filtered=>matches.where((o)=>category=='all'||(o['category']??'general')==category).toList();
 List<List<Map<String,dynamic>>> get grouped{
 final groups=<String,List<Map<String,dynamic>>>{};
 for(final o in filtered){final k=o['lat'].toString()+','+o['lon'].toString();groups.putIfAbsent(k,()=>[]).add(o);}return groups.values.toList();
 }
 @override void initState(){super.initState();WidgetsBinding.instance.addObserver(this);}
 @override void dispose(){WidgetsBinding.instance.removeObserver(this);timer?.cancel();generation++;if(widget.apiOverride==null)api.close();map.dispose();super.dispose();}
 @override void didChangeAppLifecycleState(AppLifecycleState s){visible=s==AppLifecycleState.resumed;if(!visible&&s!=AppLifecycleState.inactive){stop();}}
 void stop(){timer?.cancel();generation++;mapReady=false;if(mounted)setState((){enabled=false;matches=[];position=null;baseMap=false;accuracy=null;status='Localisation désactivée.';});}
 Future<void> start()async{if(enabled)return;setState((){enabled=true;status='Recherche des offres…';});await scan();if(mounted&&enabled)timer=Timer.periodic(const Duration(seconds:45),(_)=>scan());}
 Future<void> scan()async{
 if(!enabled||busy||!visible)return;final g=generation;setState(()=>busy=true);
 try{
 final result=await api.call('/nearby');
 if(!mounted||!enabled||g!=generation)return;
 final p=await channel.invokeMapMethod<String,dynamic>('position');
 if(!mounted||!enabled||g!=generation)return;
 if(p==null)throw Exception('Position indisponible');
 final point=LatLng((p['lat'] as num).toDouble(),(p['lon'] as num).toDouble());
 final found=nearbyMatches(result['offers'] as List,point);
 setState((){position=point;accuracy=(p['accuracy'] as num?)?.toDouble();matches=found;status=found.isEmpty?'Aucune offre active dans un rayon de 1 km.':found.length.toString()+' offre(s) à proximité.';});
 if(alerts&&visible){for(final o in found){if(!mounted||!enabled||g!=generation||!visible||!alerts)break;await channel.invokeMethod('alert',{'id':o['id'].toString(),'title':o['title'],'body':o['shop'].toString()+' · '+(o['distance'] as double).round().toString()+' m environ'});}}
 }catch(e){if(mounted&&g==generation){mapReady=false;setState((){position=null;matches=[];baseMap=false;status='Localisation ou serveur indisponible. Réessayez.';});}}
 finally{if(mounted)setState(()=>busy=false);}
 }
 Future<void> toggleAlerts(bool v)async{if(!v){setState(()=>alerts=false);return;}try{final ok=await channel.invokeMethod<bool>('permissionNotifications')??false;if(mounted)setState(()=>alerts=ok);}catch(e){if(mounted)setState(()=>status='Notifications indisponibles');}}
 Future<void> toggleMap()async{
 if(baseMap){setState(()=>baseMap=false);return;}
 final accepted=await showDialog<bool>(context:context,builder:(ctx)=>AlertDialog(title:const Text('Afficher les rues ?'),content:const Text('Le fond OpenStreetMap charge les tuiles visibles auprès de son fournisseur, qui peut déduire la zone affichée et recevoir votre adresse IP. TUNIBIZ et les commerces ne reçoivent pas votre position. Le radar local reste disponible sans ce partage.'),actions:[TextButton(onPressed:()=>Navigator.pop(ctx,false),child:const Text('Rester en radar')),FilledButton(onPressed:()=>Navigator.pop(ctx,true),child:const Text('Afficher la carte'))]));
 if(mounted&&enabled&&position!=null&&accepted==true)setState(()=>baseMap=true);
 }
 void detail(Map<String,dynamic> o){final asset=nearbyAssets[o['category']];showModalBottomSheet<void>(context:context,isScrollControlled:true,useSafeArea:true,showDragHandle:true,builder:(ctx)=>Padding(padding:const EdgeInsets.fromLTRB(22,0,22,24),child:SingleChildScrollView(child:Column(crossAxisAlignment:CrossAxisAlignment.start,mainAxisSize:MainAxisSize.min,children:[
 if(asset!=null)ClipRRect(borderRadius:BorderRadius.circular(18),child:Image.asset(asset,height:156,width:double.infinity,fit:BoxFit.cover)),
 if(asset!=null)const Text('Photo illustrative',style:TextStyle(fontSize:11,color:muted)),
 const SizedBox(height:10),Text(o['title'].toString(),style:const TextStyle(fontSize:26,fontWeight:FontWeight.w800,color:ink)),
 Text(o['shop'].toString(),style:const TextStyle(fontWeight:FontWeight.bold)),Text((o['distance'] as double).round().toString()+' m à vol d’oiseau · '+(nearbyCategories[o['category']]??'Autres')),
 const SizedBox(height:15),Text(o['description'].toString()),const SizedBox(height:12),Text('Jusqu’au '+o['ends'].toString()),const SizedBox(height:10),Text(o['address'].toString()),
 const SizedBox(height:16),FilledButton.icon(onPressed:()async{await Clipboard.setData(ClipboardData(text:o['address'].toString()));if(ctx.mounted)ScaffoldMessenger.of(ctx).showSnackBar(const SnackBar(content:Text('Adresse copiée')));},icon:const Icon(Icons.copy),label:const Text('Copier l’adresse'))
 ]))));}
 Future<void> chooseOffer(List<Map<String,dynamic>> group)async{
 if(group.length==1){detail(group.first);return;}
 final picked=await showModalBottomSheet<Map<String,dynamic>>(context:context,useSafeArea:true,showDragHandle:true,builder:(ctx)=>ListView(shrinkWrap:true,children:[
 const Padding(padding:EdgeInsets.all(18),child:Text('Offres de ce commerce',style:TextStyle(fontSize:20,fontWeight:FontWeight.bold))),
 for(final o in group)ListTile(title:Text(o['title'].toString()),subtitle:Text(o['shop'].toString()),trailing:const Icon(Icons.chevron_right),onTap:()=>Navigator.pop(ctx,o))
 ]));
 if(mounted&&picked!=null&&enabled)detail(picked);
 }
 Marker groupMarker(List<Map<String,dynamic>> group){
 final o=group.first;return Marker(point:LatLng((o['lat'] as num).toDouble(),(o['lon'] as num).toDouble()),width:44,height:44,child:Semantics(button:true,label:group.length==1?o['title'].toString():group.length.toString()+' offres',child:GestureDetector(onTap:()=>chooseOffer(group),child:Container(alignment:Alignment.center,decoration:BoxDecoration(color:ink,shape:BoxShape.circle,border:Border.all(color:mint,width:2)),child:group.length==1?Icon(categoryIcon(o['category']?.toString()??'general'),color:Colors.white,size:22):Text(group.length.toString(),style:const TextStyle(color:Colors.white,fontSize:17,fontWeight:FontWeight.bold))))));
 }
 Widget mapPanel(LatLng p)=>Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
 Row(children:[Expanded(child:Text(baseMap?'Carte des offres':'Radar local · 1 km',style:const TextStyle(fontSize:19,fontWeight:FontWeight.w800,color:ink))),TextButton(onPressed:toggleMap,child:Text(baseMap?'Radar seul':'Afficher les rues'))]),
 ClipRRect(borderRadius:BorderRadius.circular(22),child:ColoredBox(color:const Color(0xFFEAF2F5),child:SizedBox(height:320,child:Stack(children:[
 FlutterMap(mapController:map,options:MapOptions(initialCenter:p,initialZoom:14.6,minZoom:12,maxZoom:18,onMapReady:()=>mapReady=true,interactionOptions:const InteractionOptions(flags:InteractiveFlag.drag|InteractiveFlag.pinchZoom|InteractiveFlag.doubleTapZoom)),children:[
 if(baseMap)TileLayer(urlTemplate:const String.fromEnvironment('NEARBY_TILE_URL',defaultValue:'https://tile.openstreetmap.org/{z}/{x}/{y}.png'),userAgentPackageName:'tn.tunibiz.tunibiz_mobile',panBuffer:0,keepBuffer:0,maxNativeZoom:19),
 CircleLayer(circles:[CircleMarker(point:p,radius:1000,useRadiusInMeter:true,color:cobalt.withValues(alpha:.09),borderColor:cobalt,borderStrokeWidth:2),if(accuracy!=null)CircleMarker(point:p,radius:math.min(accuracy!,1000),useRadiusInMeter:true,color:mint.withValues(alpha:.12),borderColor:mint,borderStrokeWidth:1)]),
 MarkerLayer(markers:[Marker(point:p,width:34,height:34,child:const Icon(Icons.my_location,color:cobalt,size:29)),...grouped.map(groupMarker)]),
 ]),
 Positioned(right:10,top:10,child:Column(children:[FloatingActionButton.small(heroTag:'near-recenter',backgroundColor:Colors.white,onPressed:(){if(mapReady)map.move(p,14.6);},child:const Icon(Icons.my_location,color:ink)),FloatingActionButton.small(heroTag:'near-zoom-in',backgroundColor:Colors.white,onPressed:(){if(mapReady)map.move(map.camera.center,math.min(18,map.camera.zoom+1));},child:const Icon(Icons.add,color:ink)),FloatingActionButton.small(heroTag:'near-zoom-out',backgroundColor:Colors.white,onPressed:(){if(mapReady)map.move(map.camera.center,math.max(12,map.camera.zoom-1));},child:const Icon(Icons.remove,color:ink))])),
 Positioned(left:10,bottom:10,child:Container(padding:const EdgeInsets.all(6),color:Colors.white,child:Text(baseMap?'© OpenStreetMap contributors':'Vous · rayon 1 km',style:const TextStyle(fontSize:10,color:ink))))
 ])))),
 const SizedBox(height:6),Text(baseMap?'openstreetmap.org/copyright · Fond externe facultatif':'Radar géographique sans fond de rues · distances à vol d’oiseau',style:const TextStyle(fontSize:11,color:muted))
 ]);
 @override Widget build(BuildContext context)=>Scaffold(backgroundColor:paper,appBar:AppBar(title:const Text('TUNIBIZ Nearby')),body:ListView(padding:const EdgeInsets.all(18),children:[
 Container(padding:const EdgeInsets.all(24),decoration:BoxDecoration(gradient:const LinearGradient(colors:[ink,Color(0xFF174158)]),borderRadius:BorderRadius.circular(22)),child:const Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Icon(Icons.radar,color:mint,size:38),SizedBox(height:10),Text('Vos bonnes adresses, tout près.',style:TextStyle(color:Colors.white,fontSize:28,fontWeight:FontWeight.w800)),SizedBox(height:8),Text('Promotions dans un rayon de 1 km · localisation volontaire et calcul local.',style:TextStyle(color:Colors.white70))])),
 const SizedBox(height:12),FilledButton(onPressed:enabled?stop:start,child:Text(enabled?'Désactiver la découverte':'Activer la découverte')),
 if(busy)const LinearProgressIndicator(),
 if(enabled)TextButton(onPressed:busy?null:scan,child:const Text('Actualiser les offres')),
 Text(status,style:const TextStyle(color:muted)),if(accuracy!=null)Text('Précision approximative : '+accuracy!.round().toString()+' m. Distances indicatives.',style:const TextStyle(color:muted,fontSize:12)),
 const SizedBox(height:12),SingleChildScrollView(scrollDirection:Axis.horizontal,child:Row(children:[for(final e in nearbyCategories.entries)Padding(padding:const EdgeInsets.only(right:7),child:FilterChip(label:Text(e.value),selected:category==e.key,onSelected:(_)=>setState(()=>category=e.key)))])),
 if(position!=null)...[const SizedBox(height:10),mapPanel(position!),const SizedBox(height:15),Text(filtered.length.toString()+' offre(s) dans cette catégorie',style:const TextStyle(fontSize:18,fontWeight:FontWeight.w800,color:ink)),if(filtered.isEmpty)const Padding(padding:EdgeInsets.symmetric(vertical:12),child:Text('Aucune offre correspondante.'))],
 for(final o in filtered)Padding(padding:const EdgeInsets.only(top:12),child:Material(color:Colors.white,borderRadius:BorderRadius.circular(18),clipBehavior:Clip.antiAlias,child:InkWell(onTap:()=>detail(o),child:Row(children:[Container(width:88,height:100,color:ink,child:nearbyAssets[o['category']]!=null?Image.asset(nearbyAssets[o['category']]!,fit:BoxFit.cover):Icon(categoryIcon(o['category']?.toString()??'general'),color:mint,size:30)),Expanded(child:Padding(padding:const EdgeInsets.all(13),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text((o['distance'] as double).round().toString()+' m · '+(nearbyCategories[o['category']]??'Autres'),style:const TextStyle(color:Color(0xFF087F78),fontSize:11,fontWeight:FontWeight.bold)),Text(o['title'].toString(),style:const TextStyle(fontSize:17,fontWeight:FontWeight.w800)),Text(o['shop'].toString(),style:const TextStyle(fontSize:12,color:muted))]))),const Padding(padding:EdgeInsets.only(right:10),child:Icon(Icons.chevron_right))])))),
 const SizedBox(height:12),SwitchListTile(title:const Text('Alertes de proximité'),subtitle:const Text('Découverte active uniquement · 3 maximum par jour'),value:alerts,onChanged:toggleAlerts),
 const Text('Votre position ne transite pas par le serveur TUNIBIZ. Le fond de rues externe est facultatif.',style:TextStyle(color:muted,fontSize:12))
 ]));
}
