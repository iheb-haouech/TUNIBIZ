import 'dart:async';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'api.dart';
double distanceMeters(double a,double b,double c,double d){
 const r=pi/180;
 final h=pow(sin((c-a)*r/2),2)+cos(a*r)*cos(c*r)*pow(sin((d-b)*r/2),2);
 return 12742000*asin(sqrt(h.clamp(0,1)));
}
class Nearby extends StatefulWidget{const Nearby({super.key});@override State<Nearby> createState()=>_NearbyState();}
class _NearbyState extends State<Nearby> with WidgetsBindingObserver{
 final api=Api();static const channel=MethodChannel('tn.tunibiz/nearby');
 Timer? timer;bool enabled=false,alerts=false,busy=false,visible=true;String status='Activez la découverte pour voir les offres à moins de 1 km.';List<Map<String,dynamic>> matches=[];
 int generation=0;
 @override void initState(){super.initState();WidgetsBinding.instance.addObserver(this);}
 @override void dispose(){WidgetsBinding.instance.removeObserver(this);timer?.cancel();generation++;api.close();super.dispose();}
 @override void didChangeAppLifecycleState(AppLifecycleState s){visible=s==AppLifecycleState.resumed;if(!visible && s!=AppLifecycleState.inactive){stop();}}
 void stop(){timer?.cancel();generation++;if(mounted)setState((){enabled=false;matches=[];status='Découverte désactivée.';});}
 Future<void> start()async{if(enabled)return;setState((){enabled=true;status='Recherche des offres…';});await scan();if(mounted&&enabled)timer=Timer.periodic(const Duration(seconds:45),(_)=>scan());}
 Future<void> scan()async{
 if(!enabled||busy||!visible)return; final g=generation;busy=true;
 try{
 final result=await api.call('/nearby');
 if(!mounted||!enabled||g!=generation)return;
 final p=await channel.invokeMapMethod<String,dynamic>('position');
 if(!mounted||!enabled||g!=generation||p==null)return;
 final lat=(p['lat'] as num).toDouble(),lon=(p['lon'] as num).toDouble();
 final found=<Map<String,dynamic>>[];
 for(final raw in result['offers'] as List){final o=Map<String,dynamic>.from(raw);final d=distanceMeters(lat,lon,(o['lat'] as num).toDouble(),(o['lon'] as num).toDouble());if(d<=1000){o['distance']=d;found.add(o);}}
 found.sort((a,b)=>(a['distance'] as double).compareTo(b['distance'] as double));
 setState((){matches=found;status=found.isEmpty?'Aucune offre active dans un rayon de 1 km.':found.length.toString()+' offre(s) à proximité · distance approximative.';});
 if(alerts&&visible){for(final o in found){if(!mounted||!enabled||g!=generation||!visible||!alerts)break;await channel.invokeMethod('alert',{'id':o['id'].toString(),'title':o['title'],'body':o['shop'].toString()+' · '+(o['distance'] as double).round().toString()+' m environ'});}}
 }catch(e){if(mounted&&g==generation){setState(()=>status='Localisation ou serveur indisponible : '+e.toString());}}
 finally{busy=false;}
 }
 Future<void> toggleAlerts(bool v)async{if(!v){setState(()=>alerts=false);return;}try{final ok=await channel.invokeMethod<bool>('permissionNotifications')??false;if(mounted)setState(()=>alerts=ok);}catch(e){if(mounted)setState(()=>status='Notifications indisponibles');}}
 @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const Text('TUNIBIZ Nearby')),body:ListView(padding:const EdgeInsets.all(18),children:[
 Container(padding:const EdgeInsets.all(24),decoration:BoxDecoration(color:const Color(0xFF091628),borderRadius:BorderRadius.circular(22)),child:const Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Icon(Icons.radar,color:Color(0xFF2DD4BF),size:42),SizedBox(height:10),Text('Découvrez les offres autour de vous.',style:TextStyle(color:Colors.white,fontSize:28,fontWeight:FontWeight.bold)),SizedBox(height:8),Text('Rayon de 1 km. Votre position est calculée sur votre téléphone, jamais envoyée au serveur ni aux commerces.',style:TextStyle(color:Colors.white70))])),
 const SizedBox(height:12),SwitchListTile(title:const Text('Alertes de proximité'),subtitle:const Text('Pendant la découverte active · 3 maximum par jour'),value:alerts,onChanged:toggleAlerts),
 FilledButton(onPressed:enabled?stop:start,child:Text(enabled?'Désactiver la découverte':'Activer la découverte')),
 if(enabled)TextButton(onPressed:scan,child:const Text('Actualiser les offres')),Text(status),
 for(final o in matches)Card(child:Padding(padding:const EdgeInsets.all(16),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text((o['distance'] as double).round().toString()+' m environ',style:const TextStyle(color:Color(0xFF087F78),fontWeight:FontWeight.bold)),Text(o['title'],style:const TextStyle(fontSize:22,fontWeight:FontWeight.bold)),Text(o['shop']),const SizedBox(height:6),Text(o['description']),Text(o['address']),Text('Jusqu’au '+o['ends'])])))
 ]));
}
