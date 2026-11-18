import 'package:flutter/material.dart';
import 'api.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'premium.dart';

typedef CardBuilder = Widget Function(Api api,Map<String,dynamic> data);
Future<void>? googleInitialization;
class ConsumerWallet extends StatefulWidget{
 final CardBuilder cardBuilder;final Api? apiOverride;
 const ConsumerWallet({super.key,required this.cardBuilder,this.apiOverride});
 @override State<ConsumerWallet> createState()=>_ConsumerWalletState();
}
class _ConsumerWalletState extends State<ConsumerWallet>{
 late final Api api=widget.apiOverride??Api();
 final name=TextEditingController(),email=TextEditingController(),password=TextEditingController();
 Map<String,dynamic>? data;bool registering=false,busy=false;String message='';
 @override void dispose(){name.dispose();email.dispose();password.dispose();if(widget.apiOverride==null)api.close();super.dispose();}
 Future<void> run(Future<void> Function() fn)async{
 if(busy)return;setState((){busy=true;message='';});
 try{await fn();}catch(e){if(mounted)setState(()=>message=e.toString().replaceFirst('Exception: ',''));}
 finally{if(mounted)setState(()=>busy=false);}
 }
 Future<void> refresh()async{final d=await api.call('/wallet');if(mounted)setState(()=>data=d);}
 Future<void> signIn()async{
 if(!email.text.contains('@')||password.text.isEmpty||(registering&&(name.text.trim().isEmpty||password.text.length<12))){setState(()=>message='Vérifiez vos informations. Nouveau compte : 12 caractères minimum.');return;}
 await run(()async{await api.init();await api.call(registering?'/wallet/register':'/wallet/login',{'name':name.text.trim(),'email':email.text.trim(),'password':password.text});password.clear();await refresh();});
 }
 Future<void> signInGoogle()async=>run(()async{
 if(!baseUrl.startsWith('https://'))throw Exception('Connexion Google disponible avec le serveur HTTPS configure.');
 await api.init();final cfg=await api.call('/google/config');
 if(cfg['enabled']!=true)throw Exception('Connexion Google non configuree.');
 final google=GoogleSignIn.instance;
 await (googleInitialization??=google.initialize(serverClientId:cfg['client_id'] as String));
 final user=await google.authenticate();final token=user.authentication.idToken;
 if(token==null)throw Exception('Jeton Google indisponible');
 await api.call('/google/login',{'id_token':token});await refresh();
 });
 Future<void> addCard()async{
 final code=await showDialog<String>(context:context,builder:(ctx){String value='';return AlertDialog(title:const Text('Ajouter une carte'),content:TextField(autocorrect:false,obscureText:true,onChanged:(v)=>value=v,decoration:const InputDecoration(labelText:'Code personnel remis par le commerce',helperText:'Ce code est différent du QR temporaire.')),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('Annuler')),FilledButton(onPressed:()=>Navigator.pop(ctx,value.trim()),child:const Text('Ajouter'))]);});
 if(!mounted||code==null||code.isEmpty)return;
 await run(()async{await api.call('/wallet/link',{'code':code});await refresh();});
 }
 Future<void> selectCard(int id)async{
 Map<String,dynamic>? selected;
 await run(()async{await api.call('/wallet/select',{'id':id});selected=await api.call('/loyalty');});
 if(!mounted||selected==null)return;
 await Navigator.push(context,MaterialPageRoute(builder:(_)=>widget.cardBuilder(api,selected!)));
 if(mounted)await run(refresh);
 }
 Future<void> unlink(int id)async{
 final ok=await showDialog<bool>(context:context,builder:(ctx)=>AlertDialog(title:const Text('Retirer cette carte ?'),content:const Text('Les points restent chez le commerçant. Vous pourrez rattacher la carte avec son code personnel valide.'),actions:[TextButton(onPressed:()=>Navigator.pop(ctx,false),child:const Text('Annuler')),FilledButton(onPressed:()=>Navigator.pop(ctx,true),child:const Text('Retirer'))]));
 if(ok==true&&mounted)await run(()async{await api.call('/wallet/unlink',{'id':id});await refresh();});
 }
 Future<void> logout()async=>run(()async{await api.call('/wallet/logout',{});if(mounted)setState(()=>data=null);});
 Future<void> deleteAccount()async{
 final google=data?['profile']?['google_linked']==true;
 final pw=await showDialog<String>(context:context,builder:(ctx){String value='';return AlertDialog(title:const Text('Supprimer mon compte'),content:SingleChildScrollView(child:Column(mainAxisSize:MainAxisSize.min,children:[const Text('Action irreversible : profil, sessions et cartes rattachees seront supprimes ou anonymises. Les transactions sans nom ou telephone restent dans les registres des commerces. Les points rattaches ne seront plus accessibles.'),const SizedBox(height:12),if(google)const Text('Une connexion Google recente est requise (5 minutes).')else TextField(obscureText:true,onChanged:(v)=>value=v,decoration:const InputDecoration(labelText:'Confirmer le mot de passe'))])),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('Annuler')),FilledButton(onPressed:()=>Navigator.pop(ctx,value),child:const Text('Supprimer definitivement'))]);});
 if(!mounted||pw==null||(!google&&pw.isEmpty))return;
 await run(()async{await api.call('/wallet/delete',{'password':pw,'confirm_google':google});if(mounted)setState((){data=null;message='Compte supprime.';});});
 }
 Widget login()=>Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
 Container(padding:const EdgeInsets.all(24),decoration:BoxDecoration(gradient:const LinearGradient(colors:[ink,Color(0xFF174158)]),borderRadius:BorderRadius.circular(23)),child:const Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Icon(Icons.account_balance_wallet_outlined,color:mint,size:40),SizedBox(height:18),Text('Toutes vos cartes. Un seul compte.',style:TextStyle(fontSize:31,fontWeight:FontWeight.w800,color:Colors.white)),SizedBox(height:10),Text('Gardez les points de chaque commerce, gratuitement.',style:TextStyle(color:Colors.white70))])),
 const SizedBox(height:24),Text(registering?'Créer mon profil':'Connexion au portefeuille',style:const TextStyle(fontSize:25,fontWeight:FontWeight.w800,color:ink)),
 const SizedBox(height:15),if(registering)...[TextField(controller:name,decoration:const InputDecoration(labelText:'Votre nom')),const SizedBox(height:10)],
 TextField(controller:email,keyboardType:TextInputType.emailAddress,autocorrect:false,decoration:const InputDecoration(labelText:'Email')),const SizedBox(height:10),
 TextField(controller:password,obscureText:true,decoration:InputDecoration(labelText:'Mot de passe',helperText:registering?'12 caractères minimum':null)),const SizedBox(height:15),
 FilledButton(onPressed:busy?null:signIn,child:Text(registering?'Créer mon portefeuille':'Se connecter')),
 OutlinedButton.icon(onPressed:busy?null:signInGoogle,icon:const Icon(Icons.account_circle_outlined),label:const Text('Continuer avec Google')),
 TextButton(onPressed:busy?null:()=>setState((){registering=!registering;message='';password.clear();}),child:Text(registering?'J’ai déjà un compte':'Créer un compte gratuit')),
 const Text('Prototype : vérification d’email et récupération du mot de passe non disponibles.',style:TextStyle(color:muted,fontSize:12))
 ]);
 Widget wallet(Map<String,dynamic> d){
 final profile=d['profile'] as Map,cards=d['cards'] as List;
 final available=cards.fold<int>(0,(total,c)=>total+(c['eligible'] as num).toInt());
 return Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
 Container(padding:const EdgeInsets.all(23),decoration:BoxDecoration(gradient:const LinearGradient(colors:[ink,Color(0xFF174158)]),borderRadius:BorderRadius.circular(23)),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
 const Text('MON PORTEFEUILLE',style:TextStyle(color:mint,fontSize:11,letterSpacing:2,fontWeight:FontWeight.bold)),
 const SizedBox(height:10),Text('Bonjour '+profile['name'].toString(),style:const TextStyle(fontSize:29,color:Colors.white,fontWeight:FontWeight.w800)),Text(profile['email'].toString(),style:const TextStyle(color:Colors.white60)),const SizedBox(height:20),
 Row(children:[Expanded(child:stat(cards.length.toString(),'Cartes actives')),Expanded(child:stat(available.toString(),'Récompenses accessibles'))])
 ])),const SizedBox(height:18),
 FilledButton.icon(onPressed:busy?null:addCard,icon:const Icon(Icons.add_card),label:const Text('Ajouter une carte')),
 const SizedBox(height:10),const Text('Mes commerces',style:TextStyle(color:ink,fontSize:24,fontWeight:FontWeight.w800)),const Text('Les points ne sont pas transférables entre commerces.',style:TextStyle(color:muted,fontSize:12)),
 if(cards.isEmpty)const Padding(padding:EdgeInsets.symmetric(vertical:30),child:Center(child:Text('Aucune carte. Demandez votre code au commerçant.'))),
 for(final card in cards)Padding(padding:const EdgeInsets.only(top:12),child:WalletCard(card:Map<String,dynamic>.from(card),onOpen:busy?null:()=>selectCard(card['id'] as int),onRemove:busy?null:()=>unlink(card['id'] as int))),
 if(profile['google_linked']==true)TextButton(onPressed:busy?null:signInGoogle,child:const Text('Reconnexion Google')),
 const SizedBox(height:28),TextButton(onPressed:busy?null:deleteAccount,child:const Text('Supprimer mon compte',style:TextStyle(color:Colors.red))),
 ]);
 }
 Widget stat(String value,String label)=>Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(value,style:const TextStyle(color:mint,fontSize:30,fontWeight:FontWeight.w800)),Text(label,style:const TextStyle(color:Colors.white70,fontSize:12))]);
 @override Widget build(BuildContext context)=>Scaffold(backgroundColor:paper,appBar:AppBar(title:const Text('Mon portefeuille'),actions:data==null?[]:[IconButton(tooltip:'Actualiser',onPressed:busy?null:()=>run(refresh),icon:const Icon(Icons.refresh)),IconButton(tooltip:'Déconnexion',onPressed:busy?null:logout,icon:const Icon(Icons.logout))]),body:ListView(padding:const EdgeInsets.all(18),children:[if(busy)const LinearProgressIndicator(),if(message.isNotEmpty)Padding(padding:const EdgeInsets.all(8),child:Text(message,style:const TextStyle(color:Colors.red))),data==null?login():wallet(data!)]));
}
class WalletCard extends StatelessWidget{
 final Map<String,dynamic> card;final VoidCallback? onOpen,onRemove;
 const WalletCard({super.key,required this.card,this.onOpen,this.onRemove});
 @override Widget build(BuildContext context)=>Material(color:Colors.white,borderRadius:BorderRadius.circular(20),clipBehavior:Clip.antiAlias,child:InkWell(onTap:onOpen,child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
 Container(width:double.infinity,padding:const EdgeInsets.all(18),decoration:const BoxDecoration(gradient:LinearGradient(colors:[ink,Color(0xFF22415D)])),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
 Row(children:[const Icon(Icons.storefront_outlined,color:mint),const SizedBox(width:8),Expanded(child:Text(card['shop'].toString(),style:const TextStyle(fontSize:20,fontWeight:FontWeight.w800,color:Colors.white))),const Icon(Icons.chevron_right,color:Colors.white)]),
 Text(card['city'].toString(),style:const TextStyle(color:Colors.white60,fontSize:12)),const SizedBox(height:20),Text(card['points'].toString()+' pts',style:const TextStyle(color:mint,fontWeight:FontWeight.w900,fontSize:34,letterSpacing:-1))])),
 Padding(padding:const EdgeInsets.symmetric(horizontal:15,vertical:6),child:Row(children:[Expanded(child:Text(card['eligible'].toString()+' récompense(s) accessible(s)',style:const TextStyle(color:muted,fontSize:12))),TextButton(onPressed:onOpen,child:const Text('Ouvrir')),IconButton(tooltip:'Retirer la carte',onPressed:onRemove,icon:const Icon(Icons.remove_circle_outline,color:muted))]))
 ])));
}
