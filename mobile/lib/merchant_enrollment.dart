import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'api.dart';
import 'merchant_identity.dart';
import 'premium.dart';
class MerchantEnrollment extends StatefulWidget{
 const MerchantEnrollment({super.key});
 @override State<MerchantEnrollment> createState()=>_MerchantEnrollmentState();
}
class _MerchantEnrollmentState extends State<MerchantEnrollment>{
 final api=Api(),form=GlobalKey<FormState>(),map=MapController();
 final values={for(final k in ['name','city','address','lat','lon','email','password','category_detail'])k:TextEditingController()};
 String? category;String message='';bool confirmed=false,streets=false,busy=false,done=false;
 LatLng? point;
 @override void dispose(){for(final c in values.values)c.dispose();api.close();map.dispose();super.dispose();}
 void place(LatLng p){if(p.latitude<30||p.latitude>38||p.longitude<7||p.longitude>12)return;setState((){point=p;confirmed=false;values['lat']!.text=p.latitude.toStringAsFixed(6);values['lon']!.text=p.longitude.toStringAsFixed(6);});}
 void fromFields(){final lat=double.tryParse(values['lat']!.text),lon=double.tryParse(values['lon']!.text);if(lat==null||lon==null||!lat.isFinite||!lon.isFinite||lat<30||lat>38||lon<7||lon>12){setState(()=>message='Coordonnées en Tunisie requises');return;}place(LatLng(lat,lon));map.move(point!,16);}
 Future<void> submit()async{
 if(busy||!form.currentState!.validate()||category==null||!confirmed||point==null){setState(()=>message='Confirmez le point exact et renseignez tous les champs.');return;}
 setState((){busy=true;message='';});
 try{await api.init();await api.call('/merchant/register',{for(final e in values.entries)if(e.key!='category_detail'||category=='other')e.key:e.value.text.trim(),'category':category,'confirmed':confirmed});if(mounted)setState(()=>done=true);}
 catch(e){if(mounted)setState(()=>message=e.toString());}
 finally{if(mounted)setState(()=>busy=false);}
 }
 Widget field(String k,String label,{bool secret=false,bool coords=false})=>Padding(padding:const EdgeInsets.only(bottom:10),child:TextFormField(controller:values[k],obscureText:secret,keyboardType:coords?const TextInputType.numberWithOptions(decimal:true,signed:true):k=='email'?TextInputType.emailAddress:TextInputType.text,decoration:InputDecoration(labelText:label),validator:(v)=>v==null||v.trim().isEmpty||(secret&&v.length<12)?'Champ requis / 12 caractères pour le mot de passe':null,onChanged:coords?(_)=>setState((){point=null;confirmed=false;}):null));
 @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const Text('Inscrire mon commerce')),body:ListView(padding:const EdgeInsets.all(18),children:[
 Container(padding:const EdgeInsets.all(24),decoration:BoxDecoration(color:ink,borderRadius:BorderRadius.circular(20)),child:const Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text('TUNIBIZ BUSINESS',style:TextStyle(color:mint,fontWeight:FontWeight.bold)),SizedBox(height:12),Text('19 DT / 30 jours',style:TextStyle(fontSize:32,fontWeight:FontWeight.w800,color:Colors.white)),Text('Paiement en espèces · activation par TUNIBIZ',style:TextStyle(color:Colors.white70))])),
 const SizedBox(height:16),
 if(done)...[const Icon(Icons.check_circle_outline,color:Colors.teal,size:60),const Text('Demande enregistrée. Votre établissement sera activé après réception du paiement et validation du point.'),FilledButton(onPressed:()=>Navigator.pop(context),child:const Text('Retour'))]
 else Form(key:form,child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
 field('name','Nom du commerce'),field('city','Ville'),DropdownButtonFormField<String>(initialValue:category,isExpanded:true,items:[for(final e in establishmentTypes.entries)DropdownMenuItem(value:e.key,child:Text(e.value))],onChanged:(v)=>setState(()=>category=v),validator:(v)=>v==null?'Choisissez un type':null,decoration:const InputDecoration(labelText:'Type d’établissement')),if(category=='other')field('category_detail','Précisez le type d’établissement'),
 const SizedBox(height:10),field('address','Adresse publique exacte'),const Text('Confirmez la position de l’entrée de votre commerce.',style:TextStyle(fontWeight:FontWeight.bold)),
 TextButton(onPressed:()async{if(streets){setState(()=>streets=false);return;}final ok=await showDialog<bool>(context:context,builder:(ctx)=>AlertDialog(title:const Text('Afficher les rues ?'),content:const Text('Le fournisseur de carte externe reçoit l’adresse IP et la zone consultée.'),actions:[TextButton(onPressed:()=>Navigator.pop(ctx,false),child:const Text('Annuler')),FilledButton(onPressed:()=>Navigator.pop(ctx,true),child:const Text('Afficher'))]));if(mounted&&ok==true)setState(()=>streets=true);},child:Text(streets?'Masquer les rues':'Afficher OpenStreetMap')),
 SizedBox(height:300,child:FlutterMap(mapController:map,options:MapOptions(initialCenter:const LatLng(34,10),initialZoom:6.5,minZoom:6,maxZoom:19,onTap:(_,p)=>place(p)),children:[
 if(streets)TileLayer(urlTemplate:'https://tile.openstreetmap.org/{z}/{x}/{y}.png',userAgentPackageName:'tn.tunibiz.tunibiz_mobile',maxNativeZoom:19),
 if(point!=null)MarkerLayer(markers:[Marker(point:point!,width:40,height:40,child:const Icon(Icons.location_pin,color:cobalt,size:38))])
 ])),if(streets)const Text('© OpenStreetMap contributors · openstreetmap.org/copyright',style:TextStyle(fontSize:11)),
 const SizedBox(height:10),field('lat','Latitude',coords:true),field('lon','Longitude',coords:true),OutlinedButton(onPressed:fromFields,child:const Text('Placer les coordonnées saisies')),
 CheckboxListTile(value:confirmed,onChanged:point==null?null:(v)=>setState(()=>confirmed=v==true),title:const Text('Je confirme le point exact et public du commerce'),controlAffinity:ListTileControlAffinity.leading),
 field('email','Email'),field('password','Mot de passe',secret:true),if(busy)const LinearProgressIndicator(),
 FilledButton(onPressed:busy?null:submit,child:const Text('Envoyer ma demande')),
 if(message.isNotEmpty)Text(message,style:const TextStyle(color:Colors.red))
 ]))
 ]));
}
