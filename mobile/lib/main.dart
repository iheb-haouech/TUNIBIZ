import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';

const blue=Color(0xFF2563EB), navy=Color(0xFF091628), teal=Color(0xFF2DD4BF);
const baseUrl=String.fromEnvironment('API_BASE',defaultValue:'http://10.0.2.2:8877');
String money(dynamic n)=>((n as num)/1000).toStringAsFixed(3)+' DT';
const states={'new':'Nouvelle','accepted':'Acceptée','completed':'Terminée','cancelled':'Annulée','pending':'En attente','confirmed':'Confirmée'};
class Api {
 final HttpClient client=HttpClient()..connectionTimeout=const Duration(seconds:10);
 final Map<String,Cookie> cookies={};
 String csrf='';
 Future<Map<String,dynamic>> call(String path,[Map<String,dynamic>? body]) async {
  final req=await client.openUrl(body==null?'GET':'POST',Uri.parse(baseUrl+'/api'+path));
  req.cookies.addAll(cookies.values);
  if(body!=null){req.headers.contentType=ContentType.json;req.headers.set('X-CSRF-Token',csrf);req.write(jsonEncode(body));}
  final res=await req.close().timeout(const Duration(seconds:15));
  for(final c in res.cookies){if(c.maxAge==0){cookies.remove(c.name);}else{cookies[c.name]=c;}}
  final decoded=jsonDecode(await res.transform(utf8.decoder).join()) as Map<String,dynamic>;
  if(res.statusCode>=400)throw Exception(decoded['error']??'Erreur serveur');
  return decoded;
 }
 Future<void> init() async{csrf=(await call('/session'))['csrf'] as String;}
 void close()=>client.close(force:true);
}
void main()=>runApp(const Tunibiz());
class Tunibiz extends StatelessWidget {
 const Tunibiz({super.key});
 @override Widget build(BuildContext context)=>MaterialApp(title:'TUNIBIZ',debugShowCheckedModeBanner:false,theme:ThemeData(useMaterial3:true,colorScheme:ColorScheme.fromSeed(seedColor:blue),scaffoldBackgroundColor:const Color(0xFFF6F8FC),inputDecorationTheme:const InputDecorationTheme(border:OutlineInputBorder()),appBarTheme:const AppBarTheme(backgroundColor:navy,foregroundColor:Colors.white)),home:const Home());
}
class Home extends StatelessWidget {
 const Home({super.key});
 @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const Text('TUNIBIZ')),body:SafeArea(child:ListView(padding:const EdgeInsets.all(22),children:[
  Container(padding:const EdgeInsets.all(24),decoration:BoxDecoration(color:navy,borderRadius:BorderRadius.circular(26)),child:const Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Icon(Icons.storefront,color:teal,size:48),SizedBox(height:22),Text('Votre commerce.\nPlus intelligent.',style:TextStyle(fontWeight:FontWeight.w800,fontSize:32,color:Colors.white)),SizedBox(height:12),Text('Une plateforme pour tous les commerces de Tunisie.',style:TextStyle(color:Colors.white70,fontSize:16))])),
  const SizedBox(height:22),FilledButton.icon(onPressed:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>const Business())),icon:const Icon(Icons.dashboard_outlined),label:const Text('Espace commerçant')),
  const SizedBox(height:12),OutlinedButton.icon(onPressed:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>const Customer())),icon:const Icon(Icons.restaurant_menu),label:const Text('Menu client · Démo')),
  const SizedBox(height:18),const Text('Prototype local • Aucun paiement réel.',textAlign:TextAlign.center)
 ])));
}
class Metric extends StatelessWidget {
 final String title,value;final IconData icon;
 const Metric(this.title,this.value,this.icon,{super.key});
 @override Widget build(BuildContext context)=>Card(child:Padding(padding:const EdgeInsets.all(14),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Icon(icon,color:blue),const SizedBox(height:8),Text(title),Text(value,style:const TextStyle(fontSize:23,fontWeight:FontWeight.bold))])));
}
class Business extends StatefulWidget{const Business({super.key});@override State<Business> createState()=>_BusinessState();}
class _BusinessState extends State<Business>{
 final api=Api();final email=TextEditingController(text:'demo@tunibiz.local'),pw=TextEditingController();
 Map<String,dynamic>? data;String error='';bool busy=false;int tab=0;
 @override void dispose(){email.dispose();pw.dispose();api.close();super.dispose();}
 Future<void> task(Future<void> Function() run)async{
  if(busy)return;setState((){busy=true;error='';});
  try{await run();}catch(e){if(mounted)setState(()=>error=e.toString());}finally{if(mounted)setState(()=>busy=false);}
 }
 Future<void> refresh()async{final d=await api.call('/business');if(mounted)setState(()=>data=d);}
 Future<void> signin()async=>task(()async{await api.init();await api.call('/login',{'email':email.text,'password':pw.text});pw.clear();await refresh();});
 Future<void> change(String kind,int id,String status)async=>task(()async{await api.call('/business/status',{'kind':kind,'id':id,'status':status});await refresh();});
 Future<void> edit([Map<String,dynamic>? item])async{
  final name=TextEditingController(text:item?['name']),cat=TextEditingController(text:item?['category']),price=TextEditingController(text:item==null?'':(item['price']/1000).toStringAsFixed(3));bool active=item==null||item['active']==1;
  final form=GlobalKey<FormState>();
  final saved=await showDialog<bool>(context:context,builder:(c)=>StatefulBuilder(builder:(c,setDialog)=>AlertDialog(title:Text(item==null?'Nouveau produit':'Modifier'),content:Form(key:form,child:SingleChildScrollView(child:Column(mainAxisSize:MainAxisSize.min,children:[TextFormField(controller:name,decoration:const InputDecoration(labelText:'Nom'),validator:(v)=>v==null||v.trim().isEmpty?'Requis':null),const SizedBox(height:12),TextFormField(controller:cat,decoration:const InputDecoration(labelText:'Catégorie'),validator:(v)=>v==null||v.trim().isEmpty?'Requis':null),const SizedBox(height:12),TextFormField(controller:price,keyboardType:const TextInputType.numberWithOptions(decimal:true),decoration:const InputDecoration(labelText:'Prix DT'),validator:(v){final x=double.tryParse((v??'').replaceAll(',','.'));return x==null||!x.isFinite||x<0||x>10000?'Prix invalide':null;}),SwitchListTile(value:active,onChanged:(x)=>setDialog(()=>active=x),title:const Text('Disponible'))]))),actions:[TextButton(onPressed:()=>Navigator.pop(c,false),child:const Text('Annuler')),FilledButton(onPressed:(){if(form.currentState!.validate())Navigator.pop(c,true);},child:const Text('Enregistrer'))])));
  if(saved==true&&mounted){final body={'id':item?['id'],'name':name.text,'category':cat.text,'price':(double.parse(price.text.replaceAll(',','.'))*1000).round(),'active':active};await task(()async{await api.call('/business/item',body);await refresh();});}
  name.dispose();cat.dispose();price.dispose();
 }
 @override Widget build(BuildContext context){
  final d=data;
  return Scaffold(appBar:AppBar(title:const Text('TUNIBIZ Business'),actions:d==null?[]:[IconButton(onPressed:busy?null:()=>task(refresh),icon:const Icon(Icons.refresh)),IconButton(onPressed:busy?null:()=>task(()async{await api.call('/logout',{});if(mounted)setState(()=>data=null);}),icon:const Icon(Icons.logout))]),bottomNavigationBar:d==null?null:NavigationBar(selectedIndex:tab,onDestinationSelected:(i)=>setState(()=>tab=i),destinations:const [NavigationDestination(icon:Icon(Icons.receipt_long),label:'Commandes'),NavigationDestination(icon:Icon(Icons.inventory_2_outlined),label:'Catalogue'),NavigationDestination(icon:Icon(Icons.event_available),label:'Réservations')]),floatingActionButton:d!=null&&tab==1?FloatingActionButton(onPressed:busy?null:()=>edit(),child:const Icon(Icons.add)):null,body:SafeArea(child:ListView(padding:const EdgeInsets.all(16),children:[
   if(busy)const LinearProgressIndicator(),if(error.isNotEmpty)Padding(padding:const EdgeInsets.all(8),child:Text(error,style:const TextStyle(color:Colors.red))),
   if(d==null)...[const SizedBox(height:24),const Text('Connexion commerçant',style:TextStyle(fontSize:28,fontWeight:FontWeight.bold)),const SizedBox(height:18),TextField(controller:email,keyboardType:TextInputType.emailAddress,decoration:const InputDecoration(labelText:'Email')),const SizedBox(height:12),TextField(controller:pw,obscureText:true,decoration:const InputDecoration(labelText:'Mot de passe')),const SizedBox(height:18),FilledButton(onPressed:busy?null:signin,child:const Text('Se connecter')),const Text('Identifiants de test : fichier mvp/data/demo-login.txt sur le PC.')]
   else ...[Text(d['shop']['name'].toString(),style:const TextStyle(fontSize:25,fontWeight:FontWeight.bold)),
    const SizedBox(height:10),Metric('Ventes clôturées',money(d['stats']['sales']),Icons.trending_up),
    Row(children:[Expanded(child:Metric('Commandes',d['stats']['orders'].toString(),Icons.receipt_long)),Expanded(child:Metric('À traiter',d['stats']['pending'].toString(),Icons.pending_actions))]),
    const SizedBox(height:14),
    if(tab==0)...[const Text('Commandes reçues',style:TextStyle(fontSize:20,fontWeight:FontWeight.bold)),if((d['orders'] as List).isEmpty)const Text('Aucune commande. Testez le menu client.'),for(final o in d['orders'])Card(child:Padding(padding:const EdgeInsets.all(14),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text('#'+o['id'].toString()+' · '+o['customer'],style:const TextStyle(fontWeight:FontWeight.bold)),Text((o['lines'] as List).map((l)=>l['qty'].toString()+' × '+l['name']).join(' · ')),Text('Table '+o['table_no']+' · '+money(o['total'])),Text(states[o['status']]??o['status']),Wrap(spacing:8,children:[if(o['status']=='new')FilledButton(onPressed:busy?null:()=>change('orders',o['id'],'accepted'),child:const Text('Accepter')),if(o['status']=='accepted')FilledButton(onPressed:busy?null:()=>change('orders',o['id'],'completed'),child:const Text('Terminer')),if(['new','accepted'].contains(o['status']))TextButton(onPressed:busy?null:()=>change('orders',o['id'],'cancelled'),child:const Text('Annuler'))])])))]
    else if(tab==1)...[const Text('Catalogue',style:TextStyle(fontSize:20,fontWeight:FontWeight.bold)),for(final i in d['items'])Card(child:ListTile(title:Text(i['name']),subtitle:Text(i['category']+' · '+money(i['price'])+' · '+(i['active']==1?'Actif':'Masqué')),trailing:IconButton(icon:const Icon(Icons.edit),onPressed:busy?null:()=>edit(Map<String,dynamic>.from(i)))))]
    else ...[const Text('Réservations',style:TextStyle(fontSize:20,fontWeight:FontWeight.bold)),if((d['reservations'] as List).isEmpty)const Text('Aucune réservation.'),for(final r in d['reservations'])Card(child:Padding(padding:const EdgeInsets.all(14),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(r['customer']+' · '+r['guests'].toString()+' pers.',style:const TextStyle(fontWeight:FontWeight.bold)),Text(r['day']+' à '+r['slot']+' · '+r['phone']),Text(states[r['status']]??r['status']),Wrap(spacing:8,children:[if(r['status']=='pending')FilledButton(onPressed:busy?null:()=>change('reservations',r['id'],'confirmed'),child:const Text('Confirmer')),if(['pending','confirmed'].contains(r['status']))TextButton(onPressed:busy?null:()=>change('reservations',r['id'],'cancelled'),child:const Text('Annuler'))])])))]
   ]
  ])));
 }
}
class Customer extends StatefulWidget{const Customer({super.key});@override State<Customer>createState()=>_CustomerState();}
class _CustomerState extends State<Customer>{
 final api=Api();final name=TextEditingController(),table=TextEditingController();final cart=<int,int>{};Map<String,dynamic>? menu;String message='';bool busy=false;
 @override void initState(){super.initState();load();}
 @override void dispose(){name.dispose();table.dispose();api.close();super.dispose();}
 Future<void> load()async{try{await api.init();final m=await api.call('/menu/demo');if(mounted)setState(()=>menu=m);}catch(e){if(mounted)setState(()=>message=e.toString());}}
 int get total=>menu==null?0:(menu!['items'] as List).fold<int>(0,(sum,i)=>sum+(i['price'] as int)*(cart[i['id']]??0));
 Future<void> order()async{
  if(name.text.trim().isEmpty){setState(()=>message='Indiquez votre prénom.');return;}
  setState(()=>busy=true);
  try{final r=await api.call('/menu/demo/order',{'customer':name.text,'table':table.text,'cart':cart.entries.where((e)=>e.value>0).map((e)=>{'id':e.key,'qty':e.value}).toList()});if(mounted)setState((){cart.clear();message='Commande #'+r['id'].toString()+' envoyée · '+money(r['total']);});}catch(e){if(mounted)setState(()=>message=e.toString());}finally{if(mounted)setState(()=>busy=false);}
 }
 Future<void> reserve()async{
  final who=TextEditingController(text:name.text),phone=TextEditingController(),guests=TextEditingController(text:'2');DateTime? day;TimeOfDay? hour;
  final ok=await showDialog<bool>(context:context,builder:(c)=>StatefulBuilder(builder:(c,setDialog)=>AlertDialog(title:const Text('Réserver une table'),content:SingleChildScrollView(child:Column(mainAxisSize:MainAxisSize.min,children:[TextField(controller:who,decoration:const InputDecoration(labelText:'Nom')),const SizedBox(height:8),TextField(controller:phone,keyboardType:TextInputType.phone,decoration:const InputDecoration(labelText:'Téléphone')),const SizedBox(height:8),TextField(controller:guests,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'Personnes')),TextButton(onPressed:()async{final n=DateTime.now();final x=await showDatePicker(context:c,firstDate:n,lastDate:n.add(const Duration(days:180)),initialDate:n);if(x!=null)setDialog(()=>day=x);},child:Text(day==null?'Choisir la date':day!.toIso8601String().substring(0,10))),TextButton(onPressed:()async{final x=await showTimePicker(context:c,initialTime:const TimeOfDay(hour:19,minute:0));if(x!=null)setDialog(()=>hour=x);},child:Text(hour==null?'Choisir l’heure':hour!.format(c)))])),actions:[TextButton(onPressed:()=>Navigator.pop(c,false),child:const Text('Annuler')),FilledButton(onPressed:()=>Navigator.pop(c,true),child:const Text('Envoyer'))])));
  if(ok==true&&mounted){if(day==null||hour==null){setState(()=>message='Date et heure requises.');}else{try{final r=await api.call('/menu/demo/reserve',{'customer':who.text,'phone':phone.text,'day':day!.toIso8601String().substring(0,10),'slot':hour!.hour.toString().padLeft(2,'0')+':'+hour!.minute.toString().padLeft(2,'0'),'guests':int.tryParse(guests.text)??0});if(mounted)setState(()=>message='Demande #'+r['id'].toString()+' envoyée. En attente.');}catch(e){if(mounted)setState(()=>message=e.toString());}}}
  who.dispose();phone.dispose();guests.dispose();
 }
 @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const Text('TUNIBIZ Customer')),body:ListView(padding:const EdgeInsets.all(16),children:[if(message.isNotEmpty)Card(child:Padding(padding:const EdgeInsets.all(12),child:Text(message))),if(menu==null)...[const Text('Chargement du menu...'),TextButton(onPressed:load,child:const Text('Réessayer'))]else...[Text(menu!['shop']['name'],style:const TextStyle(fontSize:27,fontWeight:FontWeight.bold)),const Text('Menu digital · Démonstration'),const SizedBox(height:14),for(final i in menu!['items'])Card(child:ListTile(leading:const Icon(Icons.restaurant_menu,color:blue),title:Text(i['name']),subtitle:Text(money(i['price'])),trailing:Row(mainAxisSize:MainAxisSize.min,children:[IconButton(onPressed:()=>setState(()=>cart[i['id']]=((cart[i['id']]??0)-1).clamp(0,20).toInt()),icon:const Icon(Icons.remove_circle_outline)),Text((cart[i['id']]??0).toString()),IconButton(onPressed:()=>setState(()=>cart[i['id']]=((cart[i['id']]??0)+1).clamp(0,20).toInt()),icon:const Icon(Icons.add_circle,color:blue))]))),const SizedBox(height:16),Text('Total : '+money(total),style:const TextStyle(fontSize:23,fontWeight:FontWeight.bold)),const SizedBox(height:10),TextField(controller:name,decoration:const InputDecoration(labelText:'Prénom')),const SizedBox(height:8),TextField(controller:table,decoration:const InputDecoration(labelText:'Table (facultatif)')),const SizedBox(height:12),FilledButton(onPressed:busy||!cart.values.any((x)=>x>0)?null:order,child:const Text('Envoyer la commande')),OutlinedButton(onPressed:reserve,child:const Text('Réserver une table')),const Text('Aucun paiement en ligne dans cette démo.')]]));
}
