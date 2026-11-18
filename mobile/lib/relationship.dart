import 'dart:math';
import 'package:flutter/material.dart';
import 'api.dart';
import 'nearby.dart';

const navy=Color(0xFF091628), blue=Color(0xFF2563EB), teal=Color(0xFF2DD4BF);
String money(dynamic v)=>((v as num)/1000).toStringAsFixed(3)+' DT';
String requestKey()=>List.generate(24,(_)=>Random.secure().nextInt(256).toRadixString(16).padLeft(2,'0')).join();
void main()=>runApp(const Tunibiz());
class Tunibiz extends StatelessWidget{
 const Tunibiz({super.key});
 @override Widget build(BuildContext context)=>MaterialApp(title:'TUNIBIZ',debugShowCheckedModeBanner:false,theme:ThemeData(useMaterial3:true,colorScheme:ColorScheme.fromSeed(seedColor:blue),scaffoldBackgroundColor:const Color(0xFFF5F7FB),inputDecorationTheme:const InputDecorationTheme(border:OutlineInputBorder()),appBarTheme:const AppBarTheme(backgroundColor:navy,foregroundColor:Colors.white)),home:const Home());
}
class Home extends StatelessWidget{
 const Home({super.key});
 @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const Text('TUNIBIZ')),body:ListView(padding:const EdgeInsets.all(20),children:[
  Container(padding:const EdgeInsets.all(25),decoration:BoxDecoration(color:navy,borderRadius:BorderRadius.circular(24)),child:const Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text('MARKETING & FIDÉLITÉ',style:TextStyle(color:teal,fontWeight:FontWeight.bold)),SizedBox(height:15),Text('Des clients qui reviennent.',style:TextStyle(color:Colors.white,fontSize:34,fontWeight:FontWeight.bold)),SizedBox(height:12),Text('Pour tous les commerces de Tunisie.',style:TextStyle(color:Colors.white70))])),
  const SizedBox(height:20),FilledButton.icon(onPressed:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>const Workspace(merchant:true))),icon:const Icon(Icons.people_outline),label:const Text('Espace commerçant')),
  const SizedBox(height:10),OutlinedButton.icon(onPressed:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>const Workspace(merchant:false))),icon:const Icon(Icons.card_membership),label:const Text('Ma carte fidélité')),
  const SizedBox(height:10),OutlinedButton.icon(onPressed:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>const Nearby())),icon:const Icon(Icons.radar),label:const Text('Offres autour de moi')),
  const SizedBox(height:15),const Text('Prototype local. Aucun message externe envoyé.',textAlign:TextAlign.center)]));
}
class Workspace extends StatefulWidget{final bool merchant;const Workspace({super.key,required this.merchant});@override State<Workspace> createState()=>_WorkspaceState();}
class _WorkspaceState extends State<Workspace>{
 final api=Api();final email=TextEditingController(text:'demo@tunibiz.local'),secret=TextEditingController();Map<String,dynamic>? data;String message='';bool busy=false;int tab=0;
 @override void dispose(){email.dispose();secret.dispose();api.close();super.dispose();}
 Future<void> run(Future<void> Function() task)async{if(busy)return;setState((){busy=true;message='';});try{await task();}catch(e){if(mounted)setState(()=>message=e.toString());}finally{if(mounted)setState(()=>busy=false);}}
 Future<void> refresh()async{final d=await api.call(widget.merchant?'/crm':'/loyalty');if(mounted)setState(()=>data=d);}
 Future<void> signIn()async=>run(()async{await api.init();await api.call(widget.merchant?'/login':'/loyalty/login',widget.merchant?{'email':email.text,'password':secret.text}:{'code':secret.text});secret.clear();await refresh();});
 Future<void> logout()async=>run(()async{await api.call(widget.merchant?'/logout':'/loyalty/logout',{});if(mounted)setState(()=>data=null);});
 Future<Map<String,String>?> fields(String title,Map<String,String> labels,{Map<String,String> initial=const {},List<String> optional=const []})async{
 final cs={for(final k in labels.keys)k:TextEditingController(text:initial[k]??'')};final form=GlobalKey<FormState>();
 final result=await showDialog<Map<String,String>>(context:context,builder:(ctx)=>AlertDialog(title:Text(title),content:Form(key:form,child:SingleChildScrollView(child:Column(mainAxisSize:MainAxisSize.min,children:[for(final e in labels.entries)Padding(padding:const EdgeInsets.only(bottom:12),child:TextFormField(controller:cs[e.key],decoration:InputDecoration(labelText:e.value),validator:(v)=>!optional.contains(e.key)&&(v==null||v.trim().isEmpty)?'Requis':null))]))),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('Annuler')),FilledButton(onPressed:(){if(form.currentState!.validate())Navigator.pop(ctx,{for(final e in cs.entries)e.key:e.value.text.trim()});},child:const Text('Valider'))]));
 for(final c in cs.values)c.dispose();return result;
 }
 Future<void> codeDialog(String code)async{if(!mounted)return;await showDialog<void>(context:context,builder:(ctx)=>AlertDialog(title:const Text('Code personnel à remettre au client'),content:SelectableText(code),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('Fermer'))]));}
 Future<void> addCustomer()async{
 final p=await fields('Nouveau client',{'name':'Nom','phone':'Téléphone (facultatif)'},optional:['phone']);if(p==null||!mounted)return;
 final consent=await showDialog<bool>(context:context,builder:(ctx)=>AlertDialog(title:const Text('Consentement marketing'),content:const Text('Le client a-t-il explicitement accepté les offres marketing ?'),actions:[TextButton(onPressed:()=>Navigator.pop(ctx,false),child:const Text('Non')),FilledButton(onPressed:()=>Navigator.pop(ctx,true),child:const Text('Oui'))]));if(consent==null)return;
 await run(()async{final r=await api.call('/crm/customer',{...p,'consent':consent});await refresh();await codeDialog(r['code']);});
 }
 Future<void> purchase(int id)async{final p=await fields('Enregistrer un achat',{'amount':'Montant en DT','label':'Référence (facultatif)'},optional:['label']);if(p==null)return;final amount=double.tryParse(p['amount']!.replaceAll(',','.'));if(amount==null||!amount.isFinite||amount<=0){setState(()=>message='Montant invalide');return;}await run(()async{await api.call('/crm/purchase',{'id':id,'amount':(amount*1000).round(),'label':p['label'],'key':requestKey()});await refresh();});}
 Future<void> redeem(int id)async{final rewards=(data?['rewards'] as List? ?? []).where((r)=>r['active']==1).toList();if(rewards.isEmpty){setState(()=>message='Créez une récompense.');return;}final r=await showDialog<int>(context:context,builder:(ctx)=>SimpleDialog(title:const Text('Choisir la récompense'),children:[for(final r in rewards)SimpleDialogOption(onPressed:()=>Navigator.pop(ctx,r['id']),child:Text(r['title']+' · '+r['cost'].toString()+' pts'))]));if(r==null)return;await run(()async{await api.call('/crm/redeem',{'id':id,'reward':r,'key':requestKey()});await refresh();});}
 Future<void> customerHistory(int id)async=>run(()async{final d=await api.call('/crm/customer/'+id.toString());if(!mounted)return;await showDialog<void>(context:context,builder:(ctx)=>AlertDialog(title:Text(d['customer']['name']),content:SingleChildScrollView(child:Column(mainAxisSize:MainAxisSize.min,children:[for(final x in d['history'])ListTile(title:Text(x['label']),subtitle:Text(x['created']),trailing:Text(x['points'].toString()+' pts'))])),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('Fermer'))]));});
 Future<void> campaign()async{
 final now=DateTime.now().toIso8601String().substring(0,10);
 final p=await fields('Nouvelle campagne',{'title':'Titre','description':'Offre et conditions','starts':'Début AAAA-MM-JJ','ends':'Fin AAAA-MM-JJ'},initial:{'starts':now,'ends':now});if(p==null||!mounted)return;
 final seg=await showDialog<String>(context:context,builder:(ctx)=>SimpleDialog(title:const Text('Audience consentante'),children:[for(final e in {'all':'Tous','vip':'VIP (100 DT et plus)','inactive':'Inactifs > 30 jours'}.entries)SimpleDialogOption(onPressed:()=>Navigator.pop(ctx,e.key),child:Text(e.value))]));if(seg==null)return;await run(()async{await api.call('/crm/campaign',{...p,'segment':seg});await refresh();});
 }
 Future<void> newReward()async{final p=await fields('Nouvelle récompense',{'title':'Avantage / réduction','cost':'Points requis'});if(p==null)return;await run(()async{await api.call('/crm/reward',{'title':p['title'],'cost':int.tryParse(p['cost']!)??0});await refresh();});}
 Widget panel(Widget child)=>Card(child:Padding(padding:const EdgeInsets.all(16),child:child));
 Widget metric(String label,String value)=>panel(Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(label),Text(value,style:const TextStyle(fontSize:25,fontWeight:FontWeight.bold))]));
 List<Widget> merchantView(Map<String,dynamic> d)=>[
 const Text('Relation client',style:TextStyle(fontSize:28,fontWeight:FontWeight.bold)),
 Row(children:[Expanded(child:metric('Clients',d['stats']['customers'].toString())),Expanded(child:metric('Points',d['stats']['points'].toString()))]),
 metric('Achats enregistrés',money(d['stats']['spent'])),
 if(tab==0)...[
 FilledButton.icon(onPressed:busy?null:addCustomer,icon:const Icon(Icons.person_add),label:const Text('Nouveau client')),
 for(final c in d['customers']) panel(Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(c['name'],style:const TextStyle(fontSize:18,fontWeight:FontWeight.bold)),Text(c['points'].toString()+' points · '+money(c['spent'])),Text(c['consent']==1?'Offres acceptées':'Offres désactivées'),Wrap(spacing:5,children:[TextButton(onPressed:busy?null:()=>purchase(c['id']),child:const Text('Achat')),TextButton(onPressed:busy?null:()=>redeem(c['id']),child:const Text('Récompense')),TextButton(onPressed:busy?null:()=>customerHistory(c['id']),child:const Text('Historique'))])]))
 ]else if(tab==1)...[
 FilledButton(onPressed:busy?null:campaign,child:const Text('Créer une campagne')),
 const Text('Publication dans les cartes des clients consentants.'),
 for(final c in d['campaigns'])panel(Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(c['title'],style:const TextStyle(fontWeight:FontWeight.bold)),Text(c['description']),Text(c['starts']+' au '+c['ends']),Text(c['audience'].toString()+' clients éligibles'),if(c['active']==1)TextButton(onPressed:busy?null:()=>run(()async{await api.call('/crm/campaign/stop',{'id':c['id']});await refresh();}),child:const Text('Arrêter'))]))
 ]else...[
 FilledButton(onPressed:busy?null:newReward,child:const Text('Ajouter une récompense')),
 for(final r in d['rewards'])panel(ListTile(title:Text(r['title']),trailing:Text(r['cost'].toString()+' pts')))
 ]];
 List<Widget> cardView(Map<String,dynamic> d){final c=d['customer'];return [
 Text('Bonjour '+c['name'],style:const TextStyle(fontSize:28,fontWeight:FontWeight.bold)),
 Container(padding:const EdgeInsets.all(25),decoration:BoxDecoration(color:navy,borderRadius:BorderRadius.circular(23)),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const Text('CARTE FIDÉLITÉ',style:TextStyle(color:teal,fontWeight:FontWeight.bold)),Text(d['shop'],style:const TextStyle(color:Colors.white)),const SizedBox(height:20),Text(c['points'].toString()+' pts',style:const TextStyle(color:Colors.white,fontSize:40,fontWeight:FontWeight.bold)),Text(money(c['spent'])+' d’achats',style:const TextStyle(color:Colors.white70))])),
 const SizedBox(height:16),const Text('Vos récompenses',style:TextStyle(fontSize:20,fontWeight:FontWeight.bold)),
 for(final r in d['rewards'])panel(ListTile(title:Text(r['title']),subtitle:Text(c['points']>=r['cost']?'Disponible auprès du commerçant':'Points insuffisants'),trailing:Text(r['cost'].toString()+' pts'))),
 const Text('Vos offres',style:TextStyle(fontSize:20,fontWeight:FontWeight.bold)),if((d['campaigns'] as List).isEmpty)const Text('Aucune offre disponible.'),
 for(final r in d['campaigns'])panel(ListTile(title:Text(r['title']),subtitle:Text(r['description']+'\nJusqu’au '+r['ends']))),
 if(c['consent']==1)TextButton(onPressed:busy?null:()=>run(()async{await api.call('/loyalty/optout',{});await refresh();}),child:const Text('Ne plus recevoir les offres')),
 const Text('Historique',style:TextStyle(fontSize:20,fontWeight:FontWeight.bold)),
 for(final r in d['history'])panel(ListTile(title:Text(r['label']),subtitle:Text(r['created']),trailing:Text(r['points'].toString()+' pts')))
 ];}
 @override Widget build(BuildContext context){final d=data;return Scaffold(appBar:AppBar(title:Text(widget.merchant?'TUNIBIZ Business':'TUNIBIZ Loyalty'),actions:d==null?[]:[IconButton(onPressed:busy?null:()=>run(refresh),icon:const Icon(Icons.refresh)),IconButton(onPressed:busy?null:logout,icon:const Icon(Icons.logout))]),bottomNavigationBar:widget.merchant&&d!=null?NavigationBar(selectedIndex:tab,onDestinationSelected:(v)=>setState(()=>tab=v),destinations:const [NavigationDestination(icon:Icon(Icons.people_outline),label:'Clients'),NavigationDestination(icon:Icon(Icons.campaign_outlined),label:'Campagnes'),NavigationDestination(icon:Icon(Icons.card_giftcard),label:'Avantages')]):null,body:ListView(padding:const EdgeInsets.all(16),children:[if(busy)const LinearProgressIndicator(),if(message.isNotEmpty)Text(message,style:const TextStyle(color:Colors.red)),if(d==null)...[const SizedBox(height:25),Text(widget.merchant?'Connexion commerçant':'Connectez votre carte',style:const TextStyle(fontSize:28,fontWeight:FontWeight.bold)),const SizedBox(height:15),if(widget.merchant)...[TextField(controller:email,decoration:const InputDecoration(labelText:'Email')),const SizedBox(height:10)],TextField(controller:secret,obscureText:true,decoration:InputDecoration(labelText:widget.merchant?'Mot de passe':'Code personnel')),const SizedBox(height:15),FilledButton(onPressed:busy?null:signIn,child:const Text('Se connecter'))]else ...(widget.merchant?merchantView(d):cardView(d))]));}
}
