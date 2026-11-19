import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'api.dart';
import 'premium.dart';
import 'merchant_identity.dart';
import 'business_offer.dart';

String dtPrice(dynamic n)=>((n as num)/1000).toStringAsFixed(3)+' DT';
const kinds={'promotion':'Promotion','pack':'Pack','coupon':'Coupon'};
String dayNow()=>DateTime.now().toUtc().add(const Duration(hours:1)).toIso8601String().substring(0,10);
class StoreImage extends StatelessWidget{
 final Object? id;final double height;
 const StoreImage(this.id,{super.key,this.height=160});
 @override Widget build(BuildContext context){
 final fallback=Container(height:height,color:ink,alignment:Alignment.center,child:const Icon(Icons.storefront_outlined,color:mint,size:45));
 if(id is! String||!RegExp(r'^[a-f0-9]{32}$').hasMatch(id as String))return fallback;
 return Image.network(baseUrl+'/media/store/'+(id as String),height:height,width:double.infinity,fit:BoxFit.cover,errorBuilder:(_,__,___)=>fallback);
 }
}
class StoresPage extends StatefulWidget{
 final Api api;const StoresPage({super.key,required this.api});
 @override State<StoresPage> createState()=>_StoresPageState();
}
class _StoresPageState extends State<StoresPage>{
 List rows=[];bool loading=true;String error='',query='';bool joined=false;
 @override void initState(){super.initState();load();}
 Future<void> load()async{try{final d=await widget.api.call('/stores');if(mounted)setState((){rows=d['stores'];error='';});}catch(e){if(mounted)setState(()=>error=e.toString());}finally{if(mounted)setState(()=>loading=false);}}
 @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const Text('Nos établissements'),actions:[IconButton(onPressed:load,icon:const Icon(Icons.refresh))]),body:ListView(padding:const EdgeInsets.all(18),children:[
 const Text('Découvrez le commerce local',style:TextStyle(color:ink,fontSize:28,fontWeight:FontWeight.w800)),const Text('Promotions, packs et coupons chez les établissements actifs.'),const SizedBox(height:14),
 TextField(onChanged:(v)=>setState(()=>query=v.toLowerCase()),decoration:const InputDecoration(prefixIcon:Icon(Icons.search),hintText:'Nom, ville ou type')),
 FilterChip(label:const Text('Mes commerces uniquement'),selected:joined,onSelected:(v)=>setState(()=>joined=v)),
 if(loading)const LinearProgressIndicator(),if(error.isNotEmpty)Text(error),
 for(final s in rows.where((s)=>(!joined||s['joined']==true)&&(s['name'].toString()+' '+s['city'].toString()+' '+establishmentLabel(s)).toLowerCase().contains(query)))Padding(padding:const EdgeInsets.only(top:12),child:Material(color:Colors.white,clipBehavior:Clip.antiAlias,borderRadius:BorderRadius.circular(22),child:InkWell(onTap:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>StorePage(api:widget.api,id:s['id'] as int))),child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[StoreImage(s['cover']),ListTile(title:Text(s['name'],style:const TextStyle(fontWeight:FontWeight.w800,fontSize:20)),subtitle:Text(establishmentLabel(s)+' · '+s['city'].toString()),trailing:Icon(s['joined']==true?Icons.favorite:Icons.chevron_right,color:cobalt))])))),
 if(!loading&&rows.isEmpty)const Text('Aucun établissement actif.')
 ]));
}
class StoreListing extends StatelessWidget{
 final Map offer;final Widget? action;
 const StoreListing({super.key,required this.offer,this.action});
 @override Widget build(BuildContext context)=>Card(clipBehavior:Clip.antiAlias,color:Colors.white,child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
 StoreImage(offer['photo'],height:155),Padding(padding:const EdgeInsets.all(16),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
 Text((kinds[offer['kind']]??'Offre').toUpperCase(),style:const TextStyle(color:cobalt,fontSize:11,fontWeight:FontWeight.w800,letterSpacing:1)),
 Text(offer['title'].toString(),style:const TextStyle(fontSize:22,fontWeight:FontWeight.w800,color:ink)),
 Text(offer['description'].toString()),const SizedBox(height:8),
 if(offer['kind']=='coupon')Text('-'+offer['discount'].toString()+' %',style:const TextStyle(color:cobalt,fontSize:30,fontWeight:FontWeight.w900))else if(offer['new_price']!=null)Wrap(spacing:12,crossAxisAlignment:WrapCrossAlignment.center,children:[Text(dtPrice(offer['new_price']),style:const TextStyle(fontSize:26,fontWeight:FontWeight.w900,color:cobalt)),Text(dtPrice(offer['old_price']),style:const TextStyle(decoration:TextDecoration.lineThrough,color:muted))]),
 Text('Du '+offer['starts'].toString()+' au '+offer['ends'].toString()+' inclus',style:const TextStyle(color:muted,fontSize:12)),if(action!=null)action!
 ]))
 ]));
}
class StorePage extends StatefulWidget{
 final Api api;final int id;const StorePage({super.key,required this.api,required this.id});
 @override State<StorePage> createState()=>_StorePageState();
}
class _StorePageState extends State<StorePage>{
 Map<String,dynamic>? data;String error='';bool busy=false;String filter='all';
 @override void initState(){super.initState();load();}
 Future<void> load()async{try{final d=await widget.api.call('/stores/'+widget.id.toString());if(mounted)setState((){data=d;error='';});}catch(e){if(mounted)setState((){error=e.toString();data=null;});}}
 Future<void> claim(int id)async{if(busy)return;setState(()=>busy=true);try{await widget.api.call('/storefront/coupon/claim',{'id':id});await load();}catch(e){if(mounted)setState(()=>error=e.toString());}finally{if(mounted)setState(()=>busy=false);}}
 @override Widget build(BuildContext context){final d=data;return Scaffold(appBar:AppBar(title:Text(d?['name']??'Établissement'),actions:[IconButton(onPressed:load,icon:const Icon(Icons.refresh))]),body:ListView(padding:const EdgeInsets.all(18),children:[
 if(error.isNotEmpty)Text(error,style:const TextStyle(color:Colors.red)),if(d==null&&error.isEmpty)const LinearProgressIndicator(),
 if(d!=null)...[ClipRRect(borderRadius:BorderRadius.circular(24),child:StoreImage(d['cover'],height:210)),const SizedBox(height:16),Text(d['name'],style:const TextStyle(fontSize:30,color:ink,fontWeight:FontWeight.w900)),Text(establishmentLabel(d)+' · '+d['city'].toString()),if(d['description'].toString().isNotEmpty)Text(d['description']),
 const SizedBox(height:18),Wrap(spacing:8,children:[for(final e in {'all':'Tout',...kinds}.entries)ChoiceChip(label:Text(e.value),selected:filter==e.key,onSelected:(_)=>setState(()=>filter=e.key))]),
 if((d['offers'] as List).isEmpty&&(d['nearby'] as List).isEmpty)const Padding(padding:EdgeInsets.all(16),child:Text('Aucune offre en cours.')),
 for(final o in (d['offers'] as List).where((o)=>filter=='all'||o['kind']==filter))Padding(padding:const EdgeInsets.only(top:10),child:StoreListing(offer:o,action:o['kind']=='coupon'?couponAction(o,d):null)),
 if(filter=='all'||filter=='promotion')for(final o in d['nearby'])Padding(padding:const EdgeInsets.only(top:10),child:BusinessOfferTile(offer:o,subtitle:'Promotion Nearby'))
 ] ]));}
 Widget couponAction(Map o,Map d){
 final q=(d['coupons'] as List).where((c)=>c['offer_id']==o['id']).firstOrNull;
 if(q==null)return FilledButton.icon(onPressed:busy?null:()=>claim(o['id']),icon:const Icon(Icons.local_offer_outlined),label:const Text('Obtenir mon coupon'));
 if(q['used']!=null)return const Text('Coupon déjà utilisé',style:TextStyle(color:muted));
 return Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const Text('Présentez ce code en caisse :'),SelectableText(q['code'],style:const TextStyle(fontSize:20,fontWeight:FontWeight.w800,color:cobalt)),TextButton.icon(onPressed:()=>Clipboard.setData(ClipboardData(text:q['code'])),icon:const Icon(Icons.copy),label:const Text('Copier'))]);
 }
}
class StoreManager extends StatefulWidget{
 final Api api;const StoreManager({super.key,required this.api});
 @override State<StoreManager> createState()=>_StoreManagerState();
}
class _StoreManagerState extends State<StoreManager>{
 Map<String,dynamic>? data;String error='';bool busy=false;
 @override void initState(){super.initState();load();}
 Future<void> run(Future<void> Function() f)async{if(busy)return;setState((){busy=true;error='';});try{await f();}catch(e){if(mounted)setState(()=>error=e.toString());}finally{if(mounted)setState(()=>busy=false);}}
 Future<void> load()=>run(()async{final d=await widget.api.call('/storefront/manage');if(mounted)setState(()=>data=d);});
 Future<String?> upload(String? raw)async{if(raw==null)return null;return (await widget.api.call('/storefront/photo',{'image':raw}))['id'] as String;}
 Future<void> edit(bool profile)async{
 final result=await Navigator.push<Map<String,dynamic>>(context,MaterialPageRoute(builder:(_)=>StoreEditor(profile:profile,initial:data?['profile'] as Map?)));
 if(result==null||!mounted)return;
 await run(()async{final photo=await upload(result.remove('raw') as String?);if(profile){if(photo!=null)result['cover']=photo;await widget.api.call('/storefront/profile',result);}else{result['photo']=photo;await widget.api.call('/storefront/offer',result);}final d=await widget.api.call('/storefront/manage');if(mounted)setState(()=>data=d);});
 }
 Future<void> redeem()async{
 String code='';final result=await showDialog<bool>(context:context,builder:(ctx)=>AlertDialog(title:const Text('Valider un coupon en caisse'),content:TextField(onChanged:(v)=>code=v.trim().toUpperCase(),decoration:const InputDecoration(labelText:'Code TN-…')),actions:[TextButton(onPressed:()=>Navigator.pop(ctx,false),child:const Text('Annuler')),FilledButton(onPressed:()=>Navigator.pop(ctx,true),child:const Text('Valider définitivement'))]));
 if(result!=true||!mounted)return;
 await run(()async{final d=await widget.api.call('/storefront/coupon/redeem',{'code':code});if(mounted)setState(()=>error='Coupon validé : '+d['title'].toString()+' · -'+d['discount'].toString()+' % à appliquer en caisse.');});
 }
 @override Widget build(BuildContext context){final d=data;return Scaffold(appBar:AppBar(title:const Text('Ma vitrine'),actions:[IconButton(onPressed:busy?null:load,icon:const Icon(Icons.refresh))]),body:ListView(padding:const EdgeInsets.all(18),children:[
 if(busy)const LinearProgressIndicator(),if(error.isNotEmpty)Text(error),if(d!=null)...[
 ClipRRect(borderRadius:BorderRadius.circular(22),child:StoreImage(d['profile']['cover'],height:200)),Text(d['profile']['name'],style:const TextStyle(fontWeight:FontWeight.w900,fontSize:28,color:ink)),Text(d['profile']['description']),OutlinedButton.icon(onPressed:busy?null:()=>edit(true),icon:const Icon(Icons.edit),label:const Text('Modifier la vitrine et la photo')),
 FilledButton.icon(onPressed:busy?null:()=>edit(false),icon:const Icon(Icons.add_photo_alternate),label:const Text('Créer une promotion, un pack ou un coupon')),
 OutlinedButton.icon(onPressed:busy?null:redeem,icon:const Icon(Icons.local_offer),label:const Text('Valider un coupon client')),const SizedBox(height:16),
 const Text('Mes offres',style:TextStyle(fontSize:24,fontWeight:FontWeight.w800)),for(final o in d['offers'])StoreListing(offer:o,action:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(campaignStatus(o)),if(o['active']==1)TextButton(onPressed:busy?null:()=>run(()async{await widget.api.call('/storefront/stop',{'id':o['id']});final x=await widget.api.call('/storefront/manage');if(mounted)setState(()=>data=x);}),child:const Text('Arrêter cette offre'))]))
 ] ]));}
}
class StoreEditor extends StatefulWidget{
 final bool profile;final Map? initial;const StoreEditor({super.key,required this.profile,this.initial});
 @override State<StoreEditor> createState()=>_StoreEditorState();
}
class _StoreEditorState extends State<StoreEditor>{
 final form=GlobalKey<FormState>();final values=<String,String>{};String kind='promotion',error='';String? image;bool picking=false,remove=false;
 Future<void> pick()async{setState(()=>picking=true);try{final v=await const MethodChannel('tn.tunibiz/photo').invokeMethod<String>('pick');if(v!=null&&mounted)setState((){image=v;remove=false;});}catch(e){if(mounted)setState(()=>error='Impossible de sélectionner la photo.');}finally{if(mounted)setState(()=>picking=false);}}
 Widget field(String key,String label,{String initial='',bool numeric=false,bool required=true})=>Padding(padding:const EdgeInsets.only(bottom:12),child:TextFormField(key:ValueKey(key),initialValue:initial,keyboardType:numeric?const TextInputType.numberWithOptions(decimal:true):TextInputType.text,decoration:InputDecoration(labelText:label),maxLength:key=='description'?1000:key=='title'?100:null,onSaved:(v)=>values[key]=(v??'').trim(),validator:(v)=>required&&(v==null||v.trim().isEmpty)?'Requis':null));
 void save(){
 if(!form.currentState!.validate())return;form.currentState!.save();
 if(widget.profile){Navigator.pop(context,{'description':values['description'],'cover':remove?null:widget.initial?['cover'],'raw':image});return;}
 int? price(String key){final v=double.tryParse(values[key]!.replaceAll(',','.'));return v==null||!v.isFinite||v<0||v>10000?null:(v*1000).round();}
 final old=kind=='coupon'?null:price('old'),next=kind=='coupon'?null:price('new'),discount=kind=='coupon'?int.tryParse(values['discount']??''):null;
 if(kind=='coupon'?(discount==null||discount<1||discount>100):(old==null||next==null||next>=old)){setState(()=>error='Vérifiez les prix ou la réduction.');return;}
 Navigator.pop(context,{'kind':kind,'title':values['title'],'description':values['description'],'starts':values['starts'],'ends':values['ends'],'old_price':old,'new_price':next,'discount':discount,'raw':image});
 }
 @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:Text(widget.profile?'Modifier la vitrine':'Nouvelle offre')),body:Form(key:form,child:ListView(padding:const EdgeInsets.all(18),children:[
 if(image!=null)Image.memory(base64Decode(image!),height:180,fit:BoxFit.cover)else if(widget.profile&&!remove)StoreImage(widget.initial?['cover']),
 OutlinedButton.icon(onPressed:picking?null:pick,icon:const Icon(Icons.photo_library),label:const Text('Choisir ma photo')),if(widget.profile)TextButton(onPressed:()=>setState((){remove=true;image=null;}),child:const Text('Retirer la photo')),
 if(!widget.profile)DropdownButtonFormField<String>(initialValue:kind,items:[for(final e in kinds.entries)DropdownMenuItem(value:e.key,child:Text(e.value))],onChanged:(v)=>setState(()=>kind=v!),decoration:const InputDecoration(labelText:'Type d’offre')),
 if(!widget.profile)field('title','Titre'),
 field('description',widget.profile?'Description du commerce':'Conditions et contenu du pack',initial:widget.profile?(widget.initial?['description']?.toString()??''):'',required:!widget.profile),
 if(!widget.profile)...[field('starts','Début AAAA-MM-JJ',initial:dayNow()),field('ends','Fin AAAA-MM-JJ',initial:dayNow()),if(kind=='coupon')field('discount','Réduction %',numeric:true)else...[field('old','Prix initial DT',numeric:true),field('new','Prix promotionnel DT',numeric:true)]],
 if(error.isNotEmpty)Text(error,style:const TextStyle(color:Colors.red)),FilledButton(onPressed:picking?null:save,child:const Text('Enregistrer'))
 ])));
}
