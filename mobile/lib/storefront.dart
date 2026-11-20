import 'app_language.dart';
import 'dart:convert';
import 'commerce_widgets.dart';
import 'mobile_repository.dart';
import 'external_links.dart';
import 'scan_confirmation.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
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
 final Object? id;final double height;final String? asset;final Api? api;
 const StoreImage(this.id,{super.key,this.height=160,this.asset,this.api});
 @override Widget build(BuildContext context){
 final fallback=Container(height:height,color:ink,alignment:Alignment.center,child:const Icon(Icons.storefront_outlined,color:mint,size:45));
 if(asset!=null)return Image.asset(asset!,height:height,width:double.infinity,fit:BoxFit.cover,errorBuilder:(_,__,___)=>fallback);
 if(id is! String||!RegExp(r'^[a-f0-9]{32}$').hasMatch(id as String))return fallback;
 return Image.network((api?.serverUrl??baseUrl)+'/media/store/'+(id as String),headers:api==null?null:{'Cookie':api!.cookies.values.map((c)=>'${c.name}=${c.value}').join('; ')},cacheWidth:1000,height:height,width:double.infinity,fit:BoxFit.cover,errorBuilder:(_,__,___)=>fallback);
 }
}
class StoresPage extends StatefulWidget{
 final Api api;const StoresPage({super.key,required this.api});
 @override State<StoresPage> createState()=>_StoresPageState();
}
class _StoresPageState extends State<StoresPage>{
 List rows=[];bool loading=true;String error='',query='';bool joined=false,favorites=false;String category='';
 @override void initState(){super.initState();load();}
 Future<void> load()async{try{final d=await widget.api.call('/stores');if(mounted)setState((){rows=d['stores'];error='';});}catch(e){if(mounted)setState(()=>error=e.toString());}finally{if(mounted)setState(()=>loading=false);}}
 @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const AppText('Nos établissements'),actions:[IconButton(onPressed:load,icon:const Icon(Icons.refresh))]),body:ListView(padding:const EdgeInsets.all(18),children:[
 const AppText('Découvrez le commerce local',style:TextStyle(color:ink,fontSize:28,fontWeight:FontWeight.w800)),const AppText('Promotions, packs et coupons chez les établissements actifs.'),const SizedBox(height:14),
 TextField(onChanged:(v)=>setState(()=>query=v.toLowerCase()),decoration:const AppInputDecoration(prefixIcon:Icon(Icons.search),hintText:'Nom, ville ou type')),
 DropdownButtonFormField<String>(isExpanded:true,initialValue:category,decoration:const AppInputDecoration(labelText:'Catégorie'),items:[const DropdownMenuItem(value:'',child:AppText('Toutes les catégories')),for(final e in establishmentTypes.entries)DropdownMenuItem(value:e.key,child:AppText(e.value))],onChanged:(v)=>setState(()=>category=v??'')),
 FilterChip(label:const AppText('Mes favoris'),selected:favorites,onSelected:(v)=>setState(()=>favorites=v)),
 FilterChip(label:const AppText('Mes commerces uniquement'),selected:joined,onSelected:(v)=>setState(()=>joined=v)),
 if(loading)const LinearProgressIndicator(),if(error.isNotEmpty)AppText(error),
 for(final s in rows.where((s)=>(!joined||s['joined']==true)&&(!favorites||s['favorite']==true)&&(category.isEmpty||s['category']==category)&&(s['name'].toString()+' '+s['city'].toString()+' '+establishmentLabel(s)).toLowerCase().contains(query)))Padding(padding:const EdgeInsets.only(top:12),child:Material(color:Colors.white,clipBehavior:Clip.antiAlias,borderRadius:BorderRadius.circular(22),child:InkWell(onTap:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>StorePage(api:widget.api,id:s['id'] as int))),child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[StoreImage(s['cover']??s['photo'],api:widget.api),ListTile(title:AppText(s['name'],style:const TextStyle(fontWeight:FontWeight.w800,fontSize:20)),subtitle:AppText(establishmentLabel(s)+' · '+s['city'].toString()),trailing:Icon(s['joined']==true?Icons.favorite:Icons.chevron_right,color:cobalt))])))),
 if(!loading&&rows.isEmpty)const AppText('Aucun établissement actif.')
 ]));
}
class StoreListing extends StatelessWidget{
 final Map offer;final Widget? action;final Api? api;
 const StoreListing({super.key,required this.offer,this.action,this.api});
 @override Widget build(BuildContext context)=>Card(clipBehavior:Clip.antiAlias,color:Colors.white,child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
 StoreImage(offer['photo'],height:155,api:api),Padding(padding:const EdgeInsets.all(16),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
 AppText((kinds[offer['kind']]??'Offre').toUpperCase(),style:const TextStyle(color:cobalt,fontSize:11,fontWeight:FontWeight.w800,letterSpacing:1)),
 AppText(offer['title'].toString(),style:const TextStyle(fontSize:22,fontWeight:FontWeight.w800,color:ink)),
 AppText(offer['description'].toString()),const SizedBox(height:8),
 if(offer['kind']=='coupon')AppText('-'+offer['discount'].toString()+' %',style:const TextStyle(color:cobalt,fontSize:30,fontWeight:FontWeight.w900))else if(offer['new_price']!=null)Wrap(spacing:12,crossAxisAlignment:WrapCrossAlignment.center,children:[AppText(dtPrice(offer['new_price']),style:const TextStyle(fontSize:26,fontWeight:FontWeight.w900,color:cobalt)),AppText(dtPrice(offer['old_price']),style:const TextStyle(decoration:TextDecoration.lineThrough,color:muted))]),
 AppText('Du '+offer['starts'].toString()+' au '+offer['ends'].toString()+' inclus',style:const TextStyle(color:muted,fontSize:12)),if(action!=null)action!
 ]))
 ]));
}
class StorePage extends StatefulWidget{
 final Api api;final int id;final Map<String,dynamic>? preview;const StorePage({super.key,required this.api,required this.id,this.preview});
 @override State<StorePage> createState()=>_StorePageState();
}
class _StorePageState extends State<StorePage>{
 Map<String,dynamic>? data;String error='';bool busy=false;String filter='all';
 @override void initState(){super.initState();load();}
 Future<void> load()async{try{if(widget.preview!=null){if(mounted)setState(()=>data={'offers':<dynamic>[],'gallery':<dynamic>[],'rewards':<dynamic>[],'history':<dynamic>[],'coupons':<dynamic>[],'description':'','hours':'',...widget.preview!,'preview':true,'joined':true,'favorite':false});return;}Map<String,dynamic> d;try{d=await widget.api.cached('/stores/${widget.id}');}on ApiUnavailable{final partner=await MobileRepository(widget.api).publicPartnerById(widget.id);if(partner==null)rethrow;d=partner;}if(mounted)setState((){data=d;error='';});}catch(e){if(mounted)setState((){error=e.toString();data=null;});}}
 Future<void> visit(String url)async{try{await openExternal(url);}catch(e){if(mounted)setState(()=>error=e.toString());}}
 List<Widget> publicContacts(Map d){final social=socialLinks(d['social']);final website=safeWebUrl(d['website']),phone=d['phone']?.toString()??'';return [
 if(phone.isNotEmpty)ListTile(contentPadding:EdgeInsets.zero,leading:const Icon(Icons.phone_outlined),title:AppText(phone),onTap:()=>visit('tel:'+phone)),
 Wrap(spacing:8,children:[if(social['facebook']!=null)OutlinedButton.icon(onPressed:()=>visit(social['facebook']!),icon:const Icon(Icons.facebook),label:const AppText('Facebook')),if(social['instagram']!=null)OutlinedButton.icon(onPressed:()=>visit(social['instagram']!),icon:const Icon(Icons.photo_camera_outlined),label:const AppText('Instagram')),if(website!=null)OutlinedButton.icon(onPressed:()=>visit(website),icon:const Icon(Icons.language),label:const AppText('Site Internet'))]),
 if(d['lat'] is num&&d['lon'] is num)OutlinedButton.icon(onPressed:()=>showModalBottomSheet<void>(context:context,useSafeArea:true,isScrollControlled:true,builder:(ctx)=>SizedBox(height:430,child:Column(children:[ListTile(title:AppText(d['name']),subtitle:const AppText('Localisation publique')),Expanded(child:FlutterMap(options:MapOptions(initialCenter:LatLng((d['lat'] as num).toDouble(),(d['lon'] as num).toDouble()),initialZoom:15),children:[TileLayer(urlTemplate:'https://tile.openstreetmap.org/{z}/{x}/{y}.png',userAgentPackageName:'tn.tunibiz.tunibiz_mobile'),MarkerLayer(markers:[Marker(point:LatLng((d['lat'] as num).toDouble(),(d['lon'] as num).toDouble()),child:const Icon(Icons.location_on,color:cobalt,size:40))])])),const AppText('© OpenStreetMap contributors')]))),icon:const Icon(Icons.map_outlined),label:const AppText('Voir la carte'))];}
 Future<void> useCode()async{final p=await commerceForm(context,'Code promotionnel de cet établissement',[const CommerceField('code','Code TB-…')]);if(p==null)return;setState(()=>busy=true);try{await widget.api.call('/commerce/code/use',{'shop_id':widget.id,'code':p['code']!.trim().toUpperCase()});await load();}catch(e){if(mounted)setState(()=>error=e.toString());}finally{if(mounted)setState(()=>busy=false);}}
 Future<void> join()async{if(data?['partial']==true){final yes=await showDialog<bool>(context:context,builder:(ctx)=>AlertDialog(title:const AppText('Rejoindre la fidélité'),content:const AppText('Votre compte TUNIBIZ identifie votre fidélité. Les points d’achat sont validés par le commerçant.'),actions:[TextButton(onPressed:()=>Navigator.pop(ctx,false),child:const AppText('Annuler')),FilledButton(onPressed:()=>Navigator.pop(ctx,true),child:const AppText('Confirmer'))]));if(yes!=true||!mounted)return;setState(()=>busy=true);try{final result=await widget.api.call('/wallet/store-scan',{'slug':data!['slug']});if(mounted)await showScanConfirmation(context,data!['name'].toString(),result);}catch(e){if(mounted)setState(()=>error=e.toString());}finally{if(mounted)setState(()=>busy=false);}return;}final p=await commerceForm(context,'Rejoindre ce programme',[const CommerceField('invite','Invitation personnelle (si une fiche existe)',optional:true),const CommerceField('marketing','Promotions de ce commerce',value:'no',choices:{'no':'Je garde les communications désactivées','yes':'J’accepte les offres de ce commerce'})],note:'Vous acceptez de rattacher votre fidélité à ce commerce. Confirmez votre email et ajoutez votre téléphone dans Profil avant de continuer.');if(p==null)return;setState(()=>busy=true);try{await widget.api.call('/commerce/join',{'shop_id':widget.id,'consent':true,'invite':p['invite']!.isEmpty?null:p['invite'],'marketing':p['marketing']=='yes'});await load();}catch(e){if(mounted)setState(()=>error=e.toString());}finally{if(mounted)setState(()=>busy=false);}}
 Future<void> claim(int id)async{if(busy)return;setState(()=>busy=true);try{await widget.api.call('/storefront/coupon/claim',{'id':id});await load();}catch(e){if(mounted)setState(()=>error=e.toString());}finally{if(mounted)setState(()=>busy=false);}}
 @override Widget build(BuildContext context){final d=data;return Scaffold(appBar:AppBar(title:AppText(d?['name']??'Établissement'),actions:[if(d!=null&&d['partial']!=true&&d['preview']!=true)IconButton(tooltip:tr('Favori'),onPressed:busy?null:()async{setState(()=>busy=true);try{await widget.api.call('/stores/favorite',{'id':widget.id,'favorite':d['favorite']!=true});await load();}catch(e){if(mounted)setState(()=>error=e.toString());}finally{if(mounted)setState(()=>busy=false);}},icon:Icon(d['favorite']==true?Icons.favorite:Icons.favorite_outline)),IconButton(onPressed:load,icon:const Icon(Icons.refresh))]),body:ListView(padding:const EdgeInsets.all(18),children:[
 if(error.isNotEmpty)AppText(error,style:const TextStyle(color:Colors.red)),if(d==null&&error.isEmpty)const LinearProgressIndicator(),
 if(d!=null)...[ClipRRect(borderRadius:BorderRadius.circular(24),child:StoreImage(d['cover']??d['photo'],height:210,asset:d['photoAsset'] as String?,api:widget.api)),const SizedBox(height:16),AppText(d['name'],style:const TextStyle(fontSize:30,color:ink,fontWeight:FontWeight.w900)),AppText(establishmentLabel(d)+' · '+d['city'].toString()),if((d['description']??'').toString().isNotEmpty)AppText(d['description']),
 if(d['preview']==true)const ListTile(title:AppText('Prévisualisation privée'),subtitle:AppText('Votre vitrine n’est pas publiée par cette action.')),
 if(d['partial']==true)const ListTile(contentPadding:EdgeInsets.zero,leading:Icon(Icons.verified_outlined,color:cobalt),title:AppText('Établissement partenaire'),subtitle:AppText('Informations à compléter par le commerçant.')),
 ...publicContacts(d),
 if((d['address']??'').toString().isNotEmpty)ListTile(contentPadding:EdgeInsets.zero,leading:const Icon(Icons.location_on_outlined),title:AppText(d['address'].toString())),
 if((d['hours']??'').toString().isNotEmpty)ListTile(contentPadding:EdgeInsets.zero,leading:const Icon(Icons.schedule),title:AppText(d['hours'].toString())),
 if(d['points']!=null)Card(child:ListTile(leading:const Icon(Icons.loyalty,color:cobalt),title:AppText('${d['points']} points dans ce commerce'),subtitle:AppText((d['rewards'] as List? ?? []).map((r)=>'${r['title']} · ${r['cost']} pts').join(' · ')))),
 if((d['gallery'] as List? ?? []).isNotEmpty)SizedBox(height:145,child:ListView(scrollDirection:Axis.horizontal,children:[for(final id in d['gallery'])Padding(padding:const EdgeInsetsDirectional.only(end:8),child:SizedBox(width:210,child:ClipRRect(borderRadius:BorderRadius.circular(16),child:StoreImage(id,height:145,api:widget.api))))])),
 if(d['joined']!=true)FilledButton.icon(onPressed:busy?null:join,icon:const Icon(Icons.loyalty_outlined),label:const AppText('Rejoindre la fidélité')),if(d['partial']!=true&&d['preview']!=true)OutlinedButton.icon(onPressed:busy?null:useCode,icon:const Icon(Icons.local_offer_outlined),label:const AppText('Utiliser un code promotionnel ici')),if((d['history'] as List? ?? []).isNotEmpty)ExpansionTile(title:const AppText('Mon historique'),children:[for(final h in d['history'])ListTile(title:AppText(h['label']),subtitle:AppText(h['created']),trailing:AppText('${h['points']} pts'))]),
 if((d['coupons'] as List? ?? []).isNotEmpty)commercePanel(Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const AppText('Mes coupons',style:TextStyle(fontSize:20,fontWeight:FontWeight.w800)),for(final q in d['coupons'])ListTile(contentPadding:EdgeInsets.zero,title:AppText(q['title']?.toString()??'Mon coupon'),subtitle:SelectableText(q['used']!=null?'Déjà utilisé':q['code'].toString()))])),
 const SizedBox(height:18),Wrap(spacing:8,children:[for(final e in {'all':'Tout',...kinds}.entries)ChoiceChip(label:AppText(e.value),selected:filter==e.key,onSelected:(_)=>setState(()=>filter=e.key))]),
 if((d['offers'] as List).isEmpty&&(d['nearby'] as List).isEmpty)const Padding(padding:EdgeInsets.all(16),child:AppText('Aucune offre en cours.')),
 for(final o in (d['offers'] as List).where((o)=>filter=='all'||o['kind']==filter))Padding(padding:const EdgeInsets.only(top:10),child:StoreListing(offer:o,action:o['kind']=='coupon'?couponAction(o,d):null)),
 if(filter=='all'||filter=='promotion')for(final o in d['nearby'])Padding(padding:const EdgeInsets.only(top:10),child:BusinessOfferTile(offer:o,subtitle:'Promotion Nearby'))
 ] ]));}
 Widget couponAction(Map o,Map d){
 final q=(d['coupons'] as List).where((c)=>c['offer_id']==o['id']).firstOrNull;
 if(q==null)return FilledButton.icon(onPressed:busy?null:()=>claim(o['id']),icon:const Icon(Icons.local_offer_outlined),label:const AppText('Obtenir mon coupon'));
 if(q['used']!=null)return const AppText('Coupon déjà utilisé',style:TextStyle(color:muted));
 return Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const AppText('Présentez ce code en caisse :'),SelectableText(q['code'],style:const TextStyle(fontSize:20,fontWeight:FontWeight.w800,color:cobalt)),TextButton.icon(onPressed:()=>Clipboard.setData(ClipboardData(text:q['code'])),icon:const Icon(Icons.copy),label:const AppText('Copier'))]);
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
 Future<void> edit(bool profile,{Map? offer})async{
 final result=await Navigator.push<Map<String,dynamic>>(context,MaterialPageRoute(builder:(_)=>StoreEditor(profile:profile,initial:profile ? (data?['profile'] as Map?) : offer)));
 if(result==null||!mounted)return;
 await run(()async{final photo=await upload(result.remove('raw') as String?);if(profile){if(photo!=null)result['cover']=photo;await widget.api.call('/storefront/profile',result);}else{result['photo']=photo??offer?['photo'];if(offer!=null)result['id']=offer['id'];await widget.api.call('/storefront/offer',result);}final d=await widget.api.call('/storefront/manage');if(mounted)setState(()=>data=d);});
 }
 Future<void> redeem()async{
 String code='';final result=await showDialog<bool>(context:context,builder:(ctx)=>AlertDialog(title:const AppText('Valider un coupon en caisse'),content:TextField(onChanged:(v)=>code=v.trim().toUpperCase(),decoration:const AppInputDecoration(labelText:'Code TN-…')),actions:[TextButton(onPressed:()=>Navigator.pop(ctx,false),child:const AppText('Annuler')),FilledButton(onPressed:()=>Navigator.pop(ctx,true),child:const AppText('Valider définitivement'))]));
 if(result!=true||!mounted)return;
 await run(()async{final d=await widget.api.call('/storefront/coupon/redeem',{'code':code});if(mounted)setState(()=>error='Coupon validé : '+d['title'].toString()+' · -'+d['discount'].toString()+' % à appliquer en caisse.');});
 }
 @override Widget build(BuildContext context){final d=data;return Scaffold(appBar:AppBar(title:const AppText('Ma vitrine'),actions:[IconButton(onPressed:busy?null:load,icon:const Icon(Icons.refresh))]),body:ListView(padding:const EdgeInsets.all(18),children:[
 if(busy)const LinearProgressIndicator(),if(error.isNotEmpty)AppText(error),if(d!=null)...[
 ClipRRect(borderRadius:BorderRadius.circular(22),child:StoreImage(d['profile']['cover'],height:200)),AppText(d['profile']['name'],style:const TextStyle(fontWeight:FontWeight.w900,fontSize:28,color:ink)),AppText(d['profile']['description']),OutlinedButton.icon(onPressed:busy?null:()=>edit(true),icon:const Icon(Icons.edit),label:const AppText('Modifier la vitrine et la photo')),
 FilledButton.icon(onPressed:busy?null:()=>edit(false),icon:const Icon(Icons.add_photo_alternate),label:const AppText('Créer une promotion, un pack ou un coupon')),
 OutlinedButton.icon(onPressed:busy?null:redeem,icon:const Icon(Icons.local_offer),label:const AppText('Valider un coupon client')),const SizedBox(height:16),
 OutlinedButton.icon(onPressed:busy?null:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>StorePage(api:widget.api,id:d['profile']['id']))),icon:const Icon(Icons.visibility_outlined),label:const AppText('Prévisualiser ma vitrine')),
 const AppText('Mes offres',style:TextStyle(fontSize:24,fontWeight:FontWeight.w800)),for(final o in d['offers'])StoreListing(offer:o,action:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[AppText(campaignStatus(o)),if(o['active']==1)TextButton(onPressed:busy?null:()=>edit(false,offer:o),child:const AppText('Modifier cette offre')),if(o['active']==1)TextButton(onPressed:busy?null:()=>run(()async{await widget.api.call('/storefront/stop',{'id':o['id']});final x=await widget.api.call('/storefront/manage');if(mounted)setState(()=>data=x);}),child:const AppText('Arrêter cette offre'))]))
 ] ]));}
}
class StoreEditor extends StatefulWidget{
 final bool profile;final Map? initial;const StoreEditor({super.key,required this.profile,this.initial});
 @override State<StoreEditor> createState()=>_StoreEditorState();
}
class _StoreEditorState extends State<StoreEditor>{
 final form=GlobalKey<FormState>();final values=<String,String>{};String kind='promotion',error='';String? image;bool picking=false,remove=false;
 @override void initState(){super.initState();kind=widget.initial?['kind']?.toString()??'promotion';}
 Future<void> pick()async{setState(()=>picking=true);try{final v=await const MethodChannel('tn.tunibiz/photo').invokeMethod<String>('pick');if(v!=null&&mounted)setState((){image=v;remove=false;});}catch(e){if(mounted)setState(()=>error='Impossible de sélectionner la photo.');}finally{if(mounted)setState(()=>picking=false);}}
 Widget field(String key,String label,{String initial='',bool numeric=false,bool required=true})=>Padding(padding:const EdgeInsets.only(bottom:12),child:TextFormField(key:ValueKey(key),initialValue:initial,keyboardType:numeric?const TextInputType.numberWithOptions(decimal:true):TextInputType.text,decoration:AppInputDecoration(labelText:label),maxLength:key=='description'?1000:key=='title'?100:null,onSaved:(v)=>values[key]=(v??'').trim(),validator:(v)=>required&&(v==null||v.trim().isEmpty)?'Requis':null));
 void save(){
 if(!form.currentState!.validate())return;form.currentState!.save();
 if(widget.profile){Navigator.pop(context,{'description':values['description'],'hours':values['hours'],'cover':remove?null:widget.initial?['cover'],'raw':image});return;}
 int? price(String key){final v=double.tryParse(values[key]!.replaceAll(',','.'));return v==null||!v.isFinite||v<0||v>10000?null:(v*1000).round();}
 final old=kind=='coupon'?null:price('old'),next=kind=='coupon'?null:price('new'),discount=kind=='coupon'?int.tryParse(values['discount']??''):null;
 if(kind=='coupon'?(discount==null||discount<1||discount>100):(old==null||next==null||next>=old)){setState(()=>error='Vérifiez les prix ou la réduction.');return;}
 Navigator.pop(context,{'kind':kind,'title':values['title'],'description':values['description'],'starts':values['starts'],'ends':values['ends'],'old_price':old,'new_price':next,'discount':discount,'raw':image});
 }
 @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:AppText(widget.profile?'Modifier la vitrine':'Nouvelle offre')),body:Form(key:form,child:ListView(padding:const EdgeInsets.all(18),children:[
 if(image!=null)Image.memory(base64Decode(image!),height:180,fit:BoxFit.cover)else if(widget.profile&&!remove)StoreImage(widget.initial?['cover']),
 OutlinedButton.icon(onPressed:picking?null:pick,icon:const Icon(Icons.photo_library),label:const AppText('Choisir ma photo')),if(widget.profile)TextButton(onPressed:()=>setState((){remove=true;image=null;}),child:const AppText('Retirer la photo')),
 if(!widget.profile)DropdownButtonFormField<String>(initialValue:kind,items:[for(final e in kinds.entries)DropdownMenuItem(value:e.key,child:AppText(e.value))],onChanged:(v)=>setState(()=>kind=v!),decoration:const AppInputDecoration(labelText:'Type d’offre')),
 if(!widget.profile)field('title','Titre',initial:widget.initial?['title']?.toString()??''),
 field('description',widget.profile?'Description du commerce':'Conditions et contenu du pack',initial:widget.initial?['description']?.toString()??'',required:!widget.profile),
 if(widget.profile)field('hours','Horaires',initial:widget.initial?['hours']?.toString()??'',required:false),
 if(!widget.profile)...[field('starts','Début AAAA-MM-JJ',initial:widget.initial?['starts']?.toString()??dayNow()),field('ends','Fin AAAA-MM-JJ',initial:widget.initial?['ends']?.toString()??dayNow()),if(kind=='coupon')field('discount','Réduction %',numeric:true,initial:widget.initial?['discount']?.toString()??'')else...[field('old','Prix initial DT',numeric:true,initial:widget.initial?['old_price']==null?'':((widget.initial!['old_price'] as num)/1000).toString()),field('new','Prix promotionnel DT',numeric:true,initial:widget.initial?['new_price']==null?'':((widget.initial!['new_price'] as num)/1000).toString())]],
 if(error.isNotEmpty)AppText(error,style:const TextStyle(color:Colors.red)),FilledButton(onPressed:picking?null:save,child:const AppText('Enregistrer'))
 ])));
}
