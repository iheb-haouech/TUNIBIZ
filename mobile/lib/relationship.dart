import 'dart:math';
import 'dart:async';
import 'usage_analytics.dart';
import 'package:flutter/material.dart';
import 'api.dart';
import 'password_recovery.dart';
import 'nearby.dart';
import 'premium.dart';
import 'loyalty_qr.dart';
import 'reward_tile.dart';
import 'wallet.dart';
import 'business_dashboard.dart';
import 'checkout_scanner.dart';
import 'store_scan.dart';
import 'update_center.dart';
import 'merchant_enrollment.dart';

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
 void open(BuildContext context,int index){
  if(index==0)return;
  unawaited(Api.usage(index==1?'wallet_open':index==2?'nearby_open':'business_open'));
  Navigator.push(context,MaterialPageRoute(builder:(_)=>index==2?const Nearby():index==3?const Workspace(merchant:true):ConsumerWallet(cardBuilder:(api,data)=>Workspace(merchant:false,sharedApi:api,initialData:data))));
 }
 @override Widget build(BuildContext context)=>Scaffold(backgroundColor:paper,body:SafeArea(bottom:false,child:ListView(padding:EdgeInsets.zero,children:[
 PremiumHero(name:'Bienvenue.',shop:'Vos commerces. Vos avantages.',description:'Connectez votre carte pour suivre vos points et découvrir vos récompenses.',action:'Ma carte fidélité',points:0,goal:100,signedIn:false,onAction:()=>open(context,1)),
 Padding(padding:const EdgeInsets.fromLTRB(20,26,20,6),child:Row(children:[const Expanded(child:Text('À découvrir',style:TextStyle(fontSize:25,fontWeight:FontWeight.w800,color:ink))),TextButton(onPressed:()=>open(context,2),child:const Text('Nearby'))])),
 Padding(padding:const EdgeInsets.symmetric(horizontal:20),child:FeatureTile(asset:'assets/restaurant.webp',title:'De bonnes adresses, tout près',subtitle:'Explorez les offres actives dans les zones configurées.',tag:'NEARBY',onTap:()=>open(context,2))),
 const SizedBox(height:18),
 Padding(padding:const EdgeInsets.symmetric(horizontal:20),child:FeatureTile(asset:'assets/cafe.webp',title:'Vos habitudes ont de la valeur',subtitle:'Retrouvez vos avantages et récompenses chez les commerces partenaires.',tag:'FIDÉLITÉ',onTap:()=>open(context,1))),
 Padding(padding:const EdgeInsets.all(20),child:OutlinedButton.icon(onPressed:()=>open(context,3),icon:const Icon(Icons.storefront_outlined),label:const Text('Espace commerçant'))),
 const Padding(padding:EdgeInsets.symmetric(horizontal:20),child:UpdateEntry()),
 Padding(padding:const EdgeInsets.symmetric(horizontal:20),child:TextButton(onPressed:()async{final v=await UsageAnalytics.preferences(context);if(v!=null){await UsageAnalytics.change(v);if(v)await Api.usage('home_view');}},child:const Text('Préférences de statistiques'))),
 const Padding(padding:EdgeInsets.fromLTRB(20,0,20,20),child:Text('Prototype de test · Les photos illustrent les catégories, pas des offres actives.',style:TextStyle(color:muted,fontSize:12)))
 ])),bottomNavigationBar:PremiumNav(index:0,onSelected:(i)=>open(context,i)));
}
class Workspace extends StatefulWidget{final bool merchant;final Api? sharedApi;final Map<String,dynamic>? initialData;const Workspace({super.key,required this.merchant,this.sharedApi,this.initialData});@override State<Workspace> createState()=>_WorkspaceState();}
class _WorkspaceState extends State<Workspace>{
 final scroll=ScrollController();late final Api api=widget.sharedApi??Api(scope:widget.merchant?'merchant':'legacy');final email=TextEditingController(),secret=TextEditingController();Map<String,dynamic>? data;String message='';bool busy=false;int tab=0;
 @override void initState(){super.initState();data=widget.initialData;if(widget.sharedApi==null&&data==null)restoreSession();}
 Future<void> restoreSession()async{await run(()async{if(await api.restore()&&mounted){await api.init();await refresh();}});}
 @override void dispose(){scroll.dispose();email.dispose();secret.dispose();if(widget.sharedApi==null)api.close();super.dispose();}
 Future<void> run(Future<void> Function() task)async{if(busy)return;setState((){busy=true;message='';});try{await task();}catch(e){if(mounted)setState((){if(e is SessionExpired)data=null;message=e.toString();});}finally{if(mounted)setState(()=>busy=false);}}
 Future<void> refresh()async{final d=await api.call(widget.merchant?'/crm':'/loyalty');if(mounted)setState(()=>data=d);}
 Future<void> signIn()async=>run(()async{await api.init();await api.call(widget.merchant?'/login':'/loyalty/login',widget.merchant?{'email':email.text,'password':secret.text}:{'code':secret.text});secret.clear();await refresh();});
 Future<void> logout()async=>run(()async{await api.call(widget.merchant?'/logout':'/loyalty/logout',{});if(mounted){if(widget.sharedApi!=null){Navigator.pop(context);}else{setState(()=>data=null);}}});
 Future<Map<String,String>?> fields(String title,Map<String,String> labels,{Map<String,String> initial=const {},List<String> optional=const []})async{
 final values=<String,String>{...initial};final form=GlobalKey<FormState>();
 return showDialog<Map<String,String>>(context:context,builder:(ctx)=>AlertDialog(title:Text(title),content:Form(key:form,child:SingleChildScrollView(child:Column(mainAxisSize:MainAxisSize.min,children:[for(final e in labels.entries)Padding(padding:const EdgeInsets.only(bottom:12),child:TextFormField(initialValue:initial[e.key]??'',decoration:InputDecoration(labelText:e.value),onSaved:(v)=>values[e.key]=(v??'').trim(),validator:(v)=>!optional.contains(e.key)&&(v==null||v.trim().isEmpty)?'Requis':null))]))),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('Annuler')),FilledButton(onPressed:(){if(form.currentState!.validate()){form.currentState!.save();Navigator.pop(ctx,values);}},child:const Text('Valider'))]));

 }
 Future<void> codeDialog(String code)async{if(!mounted)return;await showDialog<void>(context:context,builder:(ctx)=>AlertDialog(title:const Text('Code personnel à remettre au client'),content:SelectableText(code),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('Fermer'))]));}
 Future<void> addCustomer()async{
 final p=await fields('Nouveau client',{'name':'Nom','phone':'Téléphone (facultatif)'},optional:['phone']);if(p==null||!mounted)return;
 final consent=await showDialog<bool>(context:context,builder:(ctx)=>AlertDialog(title:const Text('Consentement marketing'),content:const Text('Le client a-t-il explicitement accepté les offres marketing ?'),actions:[TextButton(onPressed:()=>Navigator.pop(ctx,false),child:const Text('Non')),FilledButton(onPressed:()=>Navigator.pop(ctx,true),child:const Text('Oui'))]));if(consent==null)return;
 await run(()async{final r=await api.call('/crm/customer',{...p,'consent':consent});await refresh();await codeDialog(r['code']);});
 }
 Future<void> purchase(int id)async{final p=await fields('Enregistrer un achat',{'amount':'Montant en DT','label':'Référence (facultatif)'},optional:['label']);if(p==null)return;final amount=double.tryParse(p['amount']!.replaceAll(',','.'));if(amount==null||!amount.isFinite||amount<=0){setState(()=>message='Montant invalide');return;}await run(()async{await api.call('/crm/purchase',{'id':id,'amount':(amount*1000).round(),'label':p['label'],'key':requestKey()});await refresh();});}
 Future<void> redeem(int id)async{final rewards=(data?['rewards'] as List? ?? []).where((r)=>r['active']==1).toList();if(rewards.isEmpty){setState(()=>message='Créez une récompense.');return;}final r=await showDialog<int>(context:context,builder:(ctx)=>SimpleDialog(title:const Text('Choisir la récompense'),children:[for(final r in rewards)SimpleDialogOption(onPressed:()=>Navigator.pop(ctx,r['id']),child:Text(r['title']+' · '+r['cost'].toString()+' pts'))]));if(r==null)return;await run(()async{await api.call('/crm/redeem',{'id':id,'reward':r,'key':requestKey()});await refresh();});}
 Future<void> identifyQr()async{
 final method=await showDialog<String>(context:context,builder:(ctx)=>SimpleDialog(title:const Text('Identifier une carte'),children:[
 SimpleDialogOption(onPressed:()=>Navigator.pop(ctx,'scan'),child:const Text('Scanner avec la caméra')),
 SimpleDialogOption(onPressed:()=>Navigator.pop(ctx,'manual'),child:const Text('Saisir le code temporaire'))
 ]));if(method==null||!mounted)return;
 String? token;
 if(method=='scan'){token=await Navigator.push<String>(context,MaterialPageRoute(builder:(_)=>const CheckoutScanner()));}
 else{final p=await fields('Identifier une carte',{'token':'Code temporaire (TNB1:…)'});token=p?['token'];}
 if(token==null||!mounted)return;if(!validCheckoutToken(token)){setState(()=>message='QR temporaire invalide');return;}
 Map<String,dynamic>? result;
 await run(()async{result=await api.call('/crm/qr/resolve',{'token':token});});
 if(!mounted||result==null)return;final c=result!['customer'];
 final choice=await showDialog<String>(context:context,builder:(ctx)=>AlertDialog(title:Text(c['name']),content:Text(c['points'].toString()+' points · Carte identifiée. Aucune transaction effectuée.'),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('Fermer')),TextButton(onPressed:()=>Navigator.pop(ctx,'purchase'),child:const Text('Achat')),TextButton(onPressed:()=>Navigator.pop(ctx,'redeem'),child:const Text('Récompense'))]));
 if(choice!=null&&mounted){if(choice=='purchase'){await purchase(c['id']);}else{await redeem(c['id']);}}
 }
 Future<void> customerHistory(int id)async=>run(()async{final d=await api.call('/crm/customer/'+id.toString());if(!mounted)return;await showDialog<void>(context:context,builder:(ctx)=>AlertDialog(title:Text(d['customer']['name']),content:SingleChildScrollView(child:Column(mainAxisSize:MainAxisSize.min,children:[for(final x in d['history'])ListTile(title:Text(x['label']),subtitle:Text(x['created']),trailing:Text(x['points'].toString()+' pts'))])),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('Fermer'))]));});
 Future<void> campaign()async{
 final now=DateTime.now().toIso8601String().substring(0,10);
 final p=await fields('Nouvelle campagne',{'title':'Titre','description':'Offre et conditions','starts':'Début AAAA-MM-JJ','ends':'Fin AAAA-MM-JJ'},initial:{'starts':now,'ends':now});if(p==null||!mounted)return;
 final seg=await showDialog<String>(context:context,builder:(ctx)=>SimpleDialog(title:const Text('Audience consentante'),children:[for(final e in {'all':'Tous','vip':'VIP (100 DT et plus)','inactive':'Inactifs > 30 jours'}.entries)SimpleDialogOption(onPressed:()=>Navigator.pop(ctx,e.key),child:Text(e.value))]));if(seg==null)return;await run(()async{await api.call('/crm/campaign',{...p,'segment':seg});await refresh();});
 }
 Future<void> newReward()async{
 final p=await fields('Nouvelle récompense',{'title':'Avantage / réduction','cost':'Points requis','description':'Conditions (facultatives)'},optional:['description']);if(p==null||!mounted)return;
 final visual=await showDialog<String>(context:context,builder:(ctx)=>SimpleDialog(title:const Text('Choisir un visuel illustratif'),children:[for(final e in rewardVisuals.entries)SimpleDialogOption(onPressed:()=>Navigator.pop(ctx,e.key),child:Text(e.value))]));if(visual==null)return;
 await run(()async{await api.call('/crm/reward',{'title':p['title'],'cost':int.tryParse(p['cost']!)??0,'description':p['description'],'visual':visual});await refresh();});
 }
 Future<void> manageNearby()async{
 Map<String,dynamic>? result;
 await run(()async{result=await api.call('/nearby/business');});if(!mounted||result==null)return;
 final d=result!,loc=(d['location'] as Map?)??{};
 final action=await showDialog<String>(context:context,builder:(ctx)=>SimpleDialog(title:const Text('Nearby Business'),children:[
 SimpleDialogOption(onPressed:()=>Navigator.pop(ctx,'location'),child:const Text('Configurer mon établissement')),
 SimpleDialogOption(onPressed:()=>Navigator.pop(ctx,'offer'),child:const Text('Créer une promotion')),
 for(final o in d['offers'])if(o['active']==1)SimpleDialogOption(onPressed:()=>Navigator.pop(ctx,'stop:'+o['id'].toString()),child:Text('Arrêter : '+o['title'].toString()))
 ]));if(!mounted||action==null)return;
 if(action=='location'){final p=await fields('Localisation fixe',{'address':'Adresse publique','lat':'Latitude','lon':'Longitude'},initial:{for(final k in ['address','lat','lon'])k:loc[k]?.toString()??''});if(p!=null)await run(()async{await api.call('/nearby/location',p);await refresh();});}
 else if(action=='offer'){final day=DateTime.now().toIso8601String().substring(0,10);final p=await fields('Nouvelle promotion',{'title':'Titre','description':'Conditions','starts':'Début AAAA-MM-JJ','ends':'Fin AAAA-MM-JJ'},initial:{'starts':day,'ends':day});if(p==null||!mounted)return;
 final cat=await showDialog<String>(context:context,builder:(ctx)=>SimpleDialog(title:const Text('Catégorie'),children:[for(final e in nearbyCategories.entries)if(e.key!='all')SimpleDialogOption(onPressed:()=>Navigator.pop(ctx,e.key),child:Text(e.value))]));if(cat!=null)await run(()async{await api.call('/nearby/offer',{...p,'category':cat});await refresh();});}
 else if(action.startsWith('stop:')){final ok=await showDialog<bool>(context:context,builder:(ctx)=>AlertDialog(title:const Text('Arrêter cette promotion ?'),actions:[TextButton(onPressed:()=>Navigator.pop(ctx,false),child:const Text('Annuler')),FilledButton(onPressed:()=>Navigator.pop(ctx,true),child:const Text('Arrêter'))]));if(ok==true)await run(()async{await api.call('/nearby/stop',{'id':int.parse(action.substring(5))});await refresh();});}
 }
 Widget panel(Widget child)=>Card(child:Padding(padding:const EdgeInsets.all(16),child:child));
 Widget metric(String label,String value)=>panel(Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(label),Text(value,style:const TextStyle(fontSize:25,fontWeight:FontWeight.bold))]));
 List<Widget> merchantView(Map<String,dynamic> d)=>[
 if(tab==0||tab==1)FilledButton.icon(onPressed:busy?null:()async{await Navigator.push(context,MaterialPageRoute(builder:(_)=>StoreApprovals(api:api)));if(mounted)await run(refresh);},icon:const Icon(Icons.qr_code),label:const Text('QR du commerce & validations')),
 if(tab==0)BusinessDashboard(data:d,onQr:busy?null:identifyQr,onCustomer:busy?null:addCustomer,onCampaign:busy?null:campaign,onNearby:busy?null:()=>setState(()=>tab=4)),
 if(tab==1)const Text('Mes clients',style:TextStyle(fontSize:26,fontWeight:FontWeight.w800,color:ink)),
 if(tab==1)...[
 FilledButton.icon(onPressed:busy?null:identifyQr,icon:const Icon(Icons.qr_code_scanner),label:const Text('Identifier une carte QR')),
 FilledButton.icon(onPressed:busy?null:addCustomer,icon:const Icon(Icons.person_add),label:const Text('Nouveau client')),
 for(final c in d['customers']) panel(Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(c['name'],style:const TextStyle(fontSize:18,fontWeight:FontWeight.bold)),Text(c['points'].toString()+' points · '+money(c['spent'])),Text(c['consent']==1?'Offres acceptées':'Offres désactivées'),Wrap(spacing:5,children:[TextButton(onPressed:busy?null:()=>purchase(c['id']),child:const Text('Achat')),TextButton(onPressed:busy?null:()=>redeem(c['id']),child:const Text('Récompense')),TextButton(onPressed:busy?null:()=>customerHistory(c['id']),child:const Text('Historique'))])]))
 ]else if(tab==2)...[
 FilledButton(onPressed:busy?null:campaign,child:const Text('Créer une campagne')),
 const Text('Publication dans les cartes des clients consentants.'),
 for(final c in d['campaigns'])panel(Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(c['title'],style:const TextStyle(fontWeight:FontWeight.bold)),Text(c['description']),Text(c['starts']+' au '+c['ends']),Text(c['audience'].toString()+' clients éligibles'),if(c['active']==1)TextButton(onPressed:busy?null:()=>run(()async{await api.call('/crm/campaign/stop',{'id':c['id']});await refresh();}),child:const Text('Arrêter'))]))
 ]else if(tab==3)...[
 FilledButton(onPressed:busy?null:newReward,child:const Text('Ajouter une récompense')),
 for(final r in d['rewards'])panel(ListTile(title:Text(r['title']),trailing:Text(r['cost'].toString()+' pts')))
 ]else if(tab==4)...[
 const Text('Nearby Business',style:TextStyle(fontSize:26,fontWeight:FontWeight.w800,color:ink)),
 FilledButton.icon(onPressed:busy?null:manageNearby,icon:const Icon(Icons.radar),label:const Text('Gérer les promotions et la localisation')),
 const Text('Rayons configurés · aucune position individuelle des visiteurs.')
 ]];
 List<Widget> cardView(Map<String,dynamic> d){final c=d['customer'];final points=(c['points'] as num).toInt();final rewards=(d['rewards'] as List).toList()..sort((a,b)=>(a['cost'] as num).compareTo(b['cost'] as num));final next=rewards.where((r)=>(r['cost'] as num)>points).toList();
 final goal=next.isNotEmpty?(next.first['cost'] as num).toInt():rewards.isNotEmpty?(rewards.last['cost'] as num).toInt():100;
 final description=next.isNotEmpty?'Encore '+(goal-points).toString()+' points pour votre prochaine récompense.':rewards.isEmpty?'Vos récompenses apparaîtront ici dès leur publication.':'Vous avez atteint un palier de récompense.';
 final rewardsKey=GlobalKey();
 return [
 PremiumHero(name:'Bonjour '+c['name'],shop:d['shop'].toString(),description:description,action:'Mes récompenses',points:points,goal:goal,signedIn:true,onAction:(){final ctx=rewardsKey.currentContext;if(ctx!=null){Scrollable.ensureVisible(ctx,duration:const Duration(milliseconds:350));}else if(scroll.hasClients){scroll.animateTo(min(510.0,scroll.position.maxScrollExtent),duration:const Duration(milliseconds:350),curve:Curves.easeOut);}}),
 Padding(padding:const EdgeInsets.fromLTRB(20,16,20,0),child:FilledButton.icon(onPressed:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>LoyaltyQr(api:api,shop:d['shop'].toString()))),icon:const Icon(Icons.qr_code_2),label:const Text('Présenter ma carte QR'))),
 Padding(key:rewardsKey,padding:const EdgeInsets.fromLTRB(20,26,20,12),child:const Text('Vos récompenses',style:TextStyle(fontSize:25,fontWeight:FontWeight.w800,color:ink))),
 if(rewards.isEmpty)const Padding(padding:EdgeInsets.symmetric(horizontal:20),child:Text('Aucune récompense publiée.')),
 for(final r in rewards)Padding(padding:const EdgeInsets.fromLTRB(20,0,20,16),child:RewardTile(key:ValueKey(r['id']),reward:Map<String,dynamic>.from(r),points:points)),
 const Padding(padding:EdgeInsets.fromLTRB(20,18,20,12),child:Text('Offres pour vous',style:TextStyle(fontSize:25,fontWeight:FontWeight.w800,color:ink))),
 if((d['campaigns'] as List).isEmpty)const Padding(padding:EdgeInsets.symmetric(horizontal:20),child:Text('Aucune offre disponible.')),
 for(final r in d['campaigns'])Padding(padding:const EdgeInsets.symmetric(horizontal:16),child:panel(ListTile(leading:const Icon(Icons.local_offer_outlined,color:cobalt),title:Text(r['title'],style:const TextStyle(fontWeight:FontWeight.bold)),subtitle:Text(r['description']+'\nJusqu’au '+r['ends'])))),
 Padding(padding:const EdgeInsets.all(20),child:FeatureTile(asset:'assets/restaurant.webp',title:'Explorez les offres proches',subtitle:'Découverte volontaire · Rayons configurés',tag:'NEARBY',onTap:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>const Nearby())))),
 Padding(padding:const EdgeInsets.symmetric(horizontal:20),child:Text(money(c['spent'])+' d’achats enregistrés',style:const TextStyle(color:muted))),
 if(c['consent']==1)TextButton(onPressed:busy?null:()=>run(()async{await api.call('/loyalty/optout',{});await refresh();}),child:const Text('Ne plus recevoir les offres')),
 const Padding(padding:EdgeInsets.fromLTRB(20,18,20,12),child:Text('Historique',style:TextStyle(fontSize:22,fontWeight:FontWeight.w800))),
 for(final r in d['history'])Padding(padding:const EdgeInsets.symmetric(horizontal:16),child:panel(ListTile(title:Text(r['label']),subtitle:Text(r['created']),trailing:Text(r['points'].toString()+' pts')))),
 const SizedBox(height:24)
 ];}
 @override Widget build(BuildContext context){final d=data;return Scaffold(appBar:AppBar(title:Text(widget.merchant?'TUNIBIZ Business':'TUNIBIZ Loyalty'),actions:d==null?[]:[IconButton(onPressed:busy?null:()=>run(refresh),icon:const Icon(Icons.refresh)),IconButton(onPressed:busy?null:logout,icon:const Icon(Icons.logout))]),bottomNavigationBar:widget.merchant&&d!=null?NavigationBar(selectedIndex:tab,onDestinationSelected:(v)=>setState(()=>tab=v),destinations:const [NavigationDestination(icon:Icon(Icons.dashboard_outlined),label:'Accueil'),NavigationDestination(icon:Icon(Icons.people_outline),label:'Clients'),NavigationDestination(icon:Icon(Icons.campaign_outlined),label:'Campagnes'),NavigationDestination(icon:Icon(Icons.card_giftcard),label:'Avantages'),NavigationDestination(icon:Icon(Icons.radar),label:'Nearby')]):null,body:ListView(controller:scroll,padding:!widget.merchant&&d!=null?EdgeInsets.zero:const EdgeInsets.all(16),children:[if(busy)const LinearProgressIndicator(),if(message.isNotEmpty)Text(message,style:const TextStyle(color:Colors.red)),if(d==null)...[const SizedBox(height:25),Text(widget.merchant?'Connexion commerçant':'Connectez votre carte',style:const TextStyle(fontSize:28,fontWeight:FontWeight.bold)),const SizedBox(height:15),if(widget.merchant)...[TextField(controller:email,decoration:const InputDecoration(labelText:'Email')),const SizedBox(height:10)],TextField(controller:secret,obscureText:true,decoration:InputDecoration(labelText:widget.merchant?'Mot de passe':'Code personnel')),const SizedBox(height:15),FilledButton(onPressed:busy?null:signIn,child:const Text('Se connecter')),if(widget.merchant)TextButton(onPressed:busy?null:()=>recoverPassword(context,'merchant',email.text),child:const Text('Mot de passe oublié ?')),if(widget.merchant)TextButton(onPressed:busy?null:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>const MerchantEnrollment())),child:const Text('Inscrire mon établissement'))]else ...(widget.merchant?merchantView(d):cardView(d))]));}
}
