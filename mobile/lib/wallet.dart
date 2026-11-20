import 'app_language.dart';
import 'dart:async';
import 'package:flutter/material.dart';
import 'api.dart';
import 'push_preferences.dart';
import 'store_scan.dart';
import 'scan_confirmation.dart';
import 'external_links.dart';
import 'storefront.dart';
import 'password_recovery.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'premium.dart';

typedef CardBuilder = Widget Function(Api api,Map<String,dynamic> data);
class ConsumerWalletController extends ChangeNotifier{
 bool _scanRequested=false;
 void requestScan(){_scanRequested=true;notifyListeners();}
 bool takeScanRequest(){final value=_scanRequested;_scanRequested=false;return value;}
}
Future<void>? googleInitialization;
class ConsumerWallet extends StatefulWidget{
 final Future<void> Function()? onSessionChanged;final bool profileOnly;final CardBuilder cardBuilder;final Api? apiOverride;final bool scanOnOpen,active;final ConsumerWalletController? controller;final Future<String?> Function(BuildContext)? scannerOverride;
 const ConsumerWallet({super.key,required this.cardBuilder,this.onSessionChanged,this.profileOnly=false,this.apiOverride,this.scanOnOpen=false,this.scannerOverride,this.controller,this.active=true});
 @override State<ConsumerWallet> createState()=>_ConsumerWalletState();
}
class _ConsumerWalletState extends State<ConsumerWallet>{
 late final Api api=widget.apiOverride??Api(scope:'wallet');
 final name=TextEditingController(),email=TextEditingController(),password=TextEditingController();
 Map<String,dynamic>? data,verification;bool registering=false,busy=false;String message='';
 Timer? poll;bool polling=false,restoring=true,scanPending=false,scanning=false;Map<String,String> seen={};
 @override void initState(){super.initState();scanPending=widget.scanOnOpen||(widget.controller?.takeScanRequest()??false);widget.controller?.addListener(requestedScan);restoreSession();poll=Timer.periodic(const Duration(seconds:30),(_)=>checkRequests());}
 void requestedScan(){if(widget.controller?.takeScanRequest()==true){scanPending=true;maybeScan();}}
 Future<void> restoreSession()async{
 await run(()async{if(await api.restore()&&mounted){await api.init();await refresh();}});
 if(mounted)setState(()=>restoring=false);maybeScan();
 }
 void maybeScan(){if(!mounted||!scanPending||restoring||busy||data==null)return;scanPending=false;WidgetsBinding.instance.addPostFrameCallback((_) {if(mounted)scanMerchant();});}

 Future<void> checkRequests()async{if(!mounted||!widget.active||data==null||busy||polling||WidgetsBinding.instance.lifecycleState!=AppLifecycleState.resumed||ModalRoute.of(context)?.isCurrent!=true)return;polling=true;try{final d=await api.call('/wallet/store-scans');if(!mounted||data==null)return;for(final r in d['requests']){final id=r['id'].toString(),state=r['state'].toString();if(seen[id]=='pending'&&(state=='approved'||state=='rejected')){ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:AppText(state=='approved'?'Achat validé : +'+r['points'].toString()+' points':'Demande refusée')));await refresh();}seen[id]=state;}}catch(_){}finally{polling=false;}}
 @override void dispose(){widget.controller?.removeListener(requestedScan);poll?.cancel();name.dispose();email.dispose();password.dispose();if(widget.apiOverride==null)api.close();super.dispose();}
 Future<void> run(Future<void> Function() fn)async{
 if(busy)return;setState((){busy=true;message='';});
 try{await fn();}catch(e){if(mounted)setState((){if(e is SessionExpired)data=null;message=e.toString().replaceFirst('Exception: ','');});}
 finally{if(mounted)setState(()=>busy=false);maybeScan();}
 }
 Future<void> refresh()async{
 final d=await api.call('/wallet');if(mounted)setState(()=>data=d);
 try{final v=await api.call('/verification/status');if(mounted)setState(()=>verification=v);}catch(_){/* Wallet stays available if email delivery is temporarily unavailable. */}
 }
 Future<void> verifyEmail()async=>run(()async{
 final result=await api.call('/verification/request',{});
 if(mounted)setState(()=>message=result['message']?.toString()??'Lien envoyé. Consultez votre boîte mail.');
 });
 Future<void> signIn()async{
 if(!email.text.contains('@')||password.text.isEmpty||(registering&&(name.text.trim().isEmpty||password.text.length<12))){setState(()=>message='Vérifiez vos informations. Nouveau compte : 12 caractères minimum.');return;}
 await run(()async{await api.init();await api.call(registering?'/wallet/register':'/wallet/login',{'name':name.text.trim(),'email':email.text.trim(),'password':password.text});password.clear();await refresh();await widget.onSessionChanged?.call();});
 }
 Future<void> signInGoogle()async=>run(()async{
 if(!baseUrl.startsWith('https://'))throw Exception('Connexion Google disponible avec le serveur HTTPS configure.');
 await api.init();final cfg=await api.call('/google/config');
 if(cfg['enabled']!=true)throw Exception('Connexion Google non configuree.');
 final google=GoogleSignIn.instance;
 await (googleInitialization??=google.initialize(serverClientId:cfg['client_id'] as String));
 final user=await google.authenticate();final token=user.authentication.idToken;
 if(token==null)throw Exception('Jeton Google indisponible');
 await api.call('/google/login',{'id_token':token});await refresh();await widget.onSessionChanged?.call();
 });
 Future<void> scanMerchant()async{
 if(scanning||busy||data==null)return;scanning=true;
 try{
 final slug=await (widget.scannerOverride??scanStore)(context);if(!mounted||slug==null)return;
 Map<String,dynamic>? result;String shop='';
 await run(()async{
 final info=await api.call('/store/'+slug);if(!mounted)return;
 shop=info['shop']['name'].toString();
 String? facebook=info['shop']['facebook_url']?.toString();
 if(facebook==null){try{final detail=await api.call('/stores/'+info['shop']['id'].toString());facebook=socialLinks(detail['social'])['facebook'];}catch(_){}}
 final r=await api.call('/wallet/store-scan',{'slug':slug});
 result={...r,if(facebook!=null)'facebook_url':facebook};
 if(r['id']!=null)seen[r['id'].toString()]='pending';
 await refresh();
 });
 final r=result;if(!mounted||r==null)return;
 await showScanConfirmation(context,shop,r);
 }finally{scanning=false;}
 }
 Future<void> scanHistory()async=>run(()async{
 final d=await api.call('/wallet/store-scans');if(!mounted)return;
 await showDialog<void>(context:context,builder:(ctx)=>AlertDialog(title:const AppText('Mes demandes QR'),content:SizedBox(width:300,child:SingleChildScrollView(child:Column(mainAxisSize:MainAxisSize.min,children:[if((d['requests'] as List).isEmpty)const AppText('Aucune demande.'),for(final r in d['requests'])ListTile(title:AppText(r['shop'].toString()),subtitle:AppText(r['state']=='approved'?'+'+r['points'].toString()+' points':r['state']=='pending'?'En attente':r['state']=='rejected'?'Refusée':'Expirée'))]))),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const AppText('Fermer'))]));
 await refresh();
 });
 Future<void> addCard()async{
 final code=await showDialog<String>(context:context,builder:(ctx){String value='';return AlertDialog(title:const AppText('Ajouter une carte'),content:TextField(autocorrect:false,obscureText:true,onChanged:(v)=>value=v,decoration:const AppInputDecoration(labelText:'Code personnel remis par le commerce',helperText:'Ce code est différent du QR temporaire.')),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const AppText('Annuler')),FilledButton(onPressed:()=>Navigator.pop(ctx,value.trim()),child:const AppText('Ajouter'))]);});
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
 final ok=await showDialog<bool>(context:context,builder:(ctx)=>AlertDialog(title:const AppText('Retirer cette carte ?'),content:const AppText('Les points restent chez le commerçant. Vous pourrez rattacher la carte avec son code personnel valide.'),actions:[TextButton(onPressed:()=>Navigator.pop(ctx,false),child:const AppText('Annuler')),FilledButton(onPressed:()=>Navigator.pop(ctx,true),child:const AppText('Retirer'))]));
 if(ok==true&&mounted)await run(()async{await api.call('/wallet/unlink',{'id':id});await refresh();});
 }
 Future<void> logout()async=>run(()async{await api.call('/wallet/logout',{});await PushPreferences.clearConsent(api);seen.clear();if(mounted)setState(()=>data=null);await widget.onSessionChanged?.call();});
 Future<void> deleteAccount()async{
 final google=data?['profile']?['google_linked']==true;
 final pw=await showDialog<String>(context:context,builder:(ctx){String value='';return AlertDialog(title:const AppText('Supprimer mon compte'),content:SingleChildScrollView(child:Column(mainAxisSize:MainAxisSize.min,children:[const AppText('Action irreversible : profil, sessions et cartes rattachees seront supprimes ou anonymises. Les transactions sans nom ou telephone restent dans les registres des commerces. Les points rattaches ne seront plus accessibles.'),const SizedBox(height:12),if(google)const AppText('Une connexion Google recente est requise (5 minutes).')else TextField(obscureText:true,onChanged:(v)=>value=v,decoration:const AppInputDecoration(labelText:'Confirmer le mot de passe'))])),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const AppText('Annuler')),FilledButton(onPressed:()=>Navigator.pop(ctx,value),child:const AppText('Supprimer definitivement'))]);});
 if(!mounted||pw==null||(!google&&pw.isEmpty))return;
 await run(()async{await api.call('/wallet/delete',{'password':pw,'confirm_google':google});await PushPreferences.clearConsent(api);if(mounted)setState((){data=null;message='Compte supprime.';});await widget.onSessionChanged?.call();});
 }
 Widget login()=>Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
 Container(padding:const EdgeInsets.all(24),decoration:BoxDecoration(gradient:const LinearGradient(colors:[ink,Color(0xFF174158)]),borderRadius:BorderRadius.circular(23)),child:const Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Icon(Icons.account_balance_wallet_outlined,color:mint,size:40),SizedBox(height:18),AppText('Toutes vos cartes. Un seul compte.',style:TextStyle(fontSize:31,fontWeight:FontWeight.w800,color:Colors.white)),SizedBox(height:10),AppText('Gardez les points de chaque commerce, gratuitement.',style:TextStyle(color:Colors.white70))])),
 const SizedBox(height:24),AppText(registering?'Créer mon profil':'Connexion au portefeuille',style:const TextStyle(fontSize:25,fontWeight:FontWeight.w800,color:ink)),
 const SizedBox(height:15),if(registering)...[TextField(controller:name,decoration:const AppInputDecoration(labelText:'Votre nom')),const SizedBox(height:10)],
 TextField(controller:email,keyboardType:TextInputType.emailAddress,autocorrect:false,decoration:const AppInputDecoration(labelText:'Email')),const SizedBox(height:10),
 TextField(controller:password,obscureText:true,decoration:AppInputDecoration(labelText:'Mot de passe',helperText:registering?'12 caractères minimum':null)),const SizedBox(height:15),
 FilledButton(onPressed:busy?null:signIn,child:AppText(registering?'Créer mon portefeuille':'Se connecter')),
 OutlinedButton.icon(onPressed:busy?null:signInGoogle,icon:Image.asset('assets/google_g.png',height:20,width:20),label:const AppText('Continuer avec Google')),
 TextButton(onPressed:busy?null:()=>setState((){registering=!registering;message='';password.clear();}),child:AppText(registering?'J’ai déjà un compte':'Créer un compte gratuit')),
 if(!registering)TextButton(onPressed:busy?null:()=>recoverPassword(context,'consumer',email.text),child:const AppText('Mot de passe oublié ?'))
 ]);
 Widget wallet(Map<String,dynamic> d){
 if(widget.profileOnly)return Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[if(message.isNotEmpty)AppText(message),if(verification!=null&&verification!['verified']!=true)OutlinedButton.icon(onPressed:busy?null:verifyEmail,icon:const Icon(Icons.mark_email_read_outlined),label:const AppText('Vérifier mon email')),if(PushPreferences.supported(api))PushPreferences(api:api),if(d['profile']['google_linked']==true)TextButton(onPressed:busy?null:signInGoogle,child:const AppText('Reconnexion Google')),TextButton(onPressed:busy?null:logout,child:const AppText('Déconnexion')),TextButton(onPressed:busy?null:deleteAccount,child:const AppText('Supprimer mon compte',style:TextStyle(color:Colors.red)))]);
 final profile=d['profile'] as Map,cards=d['cards'] as List;
 final available=cards.fold<int>(0,(total,c)=>total+(c['eligible'] as num).toInt());
 return Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
 Container(padding:const EdgeInsets.all(23),decoration:BoxDecoration(gradient:const LinearGradient(colors:[ink,Color(0xFF174158)]),borderRadius:BorderRadius.circular(23)),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
 const AppText('MON PORTEFEUILLE',style:TextStyle(color:mint,fontSize:11,letterSpacing:2,fontWeight:FontWeight.bold)),
 const SizedBox(height:10),AppText('Bonjour '+profile['name'].toString(),style:const TextStyle(fontSize:29,color:Colors.white,fontWeight:FontWeight.w800)),AppText(profile['email'].toString(),style:const TextStyle(color:Colors.white60)),const SizedBox(height:20),
 Row(children:[Expanded(child:stat(cards.length.toString(),'Mes cartes')),Expanded(child:stat(available.toString(),'Récompenses accessibles'))])
 ])),const SizedBox(height:18),
 if(verification!=null&&verification!['verified']!=true)Card(child:Padding(padding:const EdgeInsets.all(16),child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[const AppText('Vérifiez votre email',style:TextStyle(fontWeight:FontWeight.bold)),AppText(verification!['required']==true?'La vérification est requise pour les nouveaux scans de commerce.':'Confirmez votre adresse pour sécuriser votre compte.'),if(verification!['delivery_enabled']==true)TextButton.icon(onPressed:busy?null:verifyEmail,icon:const Icon(Icons.mark_email_read_outlined),label:const AppText('Recevoir le lien de vérification'))else const AppText('Envoi temporairement indisponible. Réessayez plus tard.')]))),
 FilledButton.icon(onPressed:busy?null:scanMerchant,icon:const Icon(Icons.qr_code_scanner),label:const AppText('Scanner le QR du commerce')),
 FilledButton.tonalIcon(onPressed:busy?null:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>StoresPage(api:api))),icon:const Icon(Icons.storefront),label:const AppText('Tous les établissements & offres')),
 OutlinedButton(onPressed:busy?null:scanHistory,child:const AppText('Mes demandes QR')),
 TextButton.icon(onPressed:busy?null:addCard,icon:const Icon(Icons.add_card),label:const AppText('Ajouter une ancienne carte par code')),
 const SizedBox(height:10),const AppText('Mes commerces',style:TextStyle(color:ink,fontSize:24,fontWeight:FontWeight.w800)),const AppText('Les points ne sont pas transférables entre commerces.',style:TextStyle(color:muted,fontSize:12)),
 if(cards.isEmpty)const Padding(padding:EdgeInsets.symmetric(vertical:30),child:Center(child:AppText('Aucune carte. Scannez le QR d’un commerce pour commencer.'))),
 for(final card in cards)Padding(padding:const EdgeInsets.only(top:12),child:WalletCard(card:Map<String,dynamic>.from(card),onOpen:busy?null:()=>selectCard(card['id'] as int),onStore:busy||card['shop_id']==null||card['archived']==1?null:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>StorePage(api:api,id:card['shop_id'] as int))),onRemove:busy?null:()=>unlink(card['id'] as int))),
 if(PushPreferences.supported(api)) PushPreferences(api:api),
 if(profile['google_linked']==true)TextButton(onPressed:busy?null:signInGoogle,child:const AppText('Reconnexion Google')),
 const SizedBox(height:28),TextButton(onPressed:busy?null:deleteAccount,child:const AppText('Supprimer mon compte',style:TextStyle(color:Colors.red))),
 ]);
 }
 Widget stat(String value,String label)=>Column(crossAxisAlignment:CrossAxisAlignment.start,children:[AppText(value,style:const TextStyle(color:mint,fontSize:30,fontWeight:FontWeight.w800)),AppText(label,style:const TextStyle(color:Colors.white70,fontSize:12))]);
 @override Widget build(BuildContext context)=>widget.profileOnly?(data==null?const SizedBox():wallet(data!)):Scaffold(backgroundColor:paper,appBar:AppBar(title:const AppText('Mon portefeuille'),actions:data==null?[]:[IconButton(tooltip:tr('Actualiser'),onPressed:busy?null:()=>run(refresh),icon:const Icon(Icons.refresh)),IconButton(tooltip:tr('Déconnexion'),onPressed:busy?null:logout,icon:const Icon(Icons.logout))]),body:ListView(padding:const EdgeInsets.all(18),children:[if(busy)const LinearProgressIndicator(),if(message.isNotEmpty)Padding(padding:const EdgeInsets.all(8),child:AppText(message,style:const TextStyle(color:Colors.red))),restoring?const Padding(padding:EdgeInsets.all(32),child:Center(child:CircularProgressIndicator())):data==null?(api.signedIn?Column(children:[const AppText('Votre compte est enregistré. Connexion au serveur indisponible.'),FilledButton(onPressed:busy?null:()=>run(()async{await api.init();await refresh();}),child:const AppText('Réessayer'))]):login()):wallet(data!)]));
}
class WalletCard extends StatelessWidget{
 final Map<String,dynamic> card;final VoidCallback? onOpen,onRemove,onStore;
 const WalletCard({super.key,required this.card,this.onOpen,this.onRemove,this.onStore});
 @override Widget build(BuildContext context)=>Material(color:Colors.white,borderRadius:BorderRadius.circular(20),clipBehavior:Clip.antiAlias,child:InkWell(onTap:onOpen,child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
 Container(width:double.infinity,padding:const EdgeInsets.all(18),decoration:const BoxDecoration(gradient:LinearGradient(colors:[ink,Color(0xFF22415D)])),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
 Row(children:[const Icon(Icons.storefront_outlined,color:mint),const SizedBox(width:8),Expanded(child:AppText(card['shop'].toString(),style:const TextStyle(fontSize:20,fontWeight:FontWeight.w800,color:Colors.white))),const Icon(Icons.chevron_right,color:Colors.white)]),
 AppText(card['city'].toString()+(card['archived']==1?' · Commerce archivé':''),style:const TextStyle(color:Colors.white60,fontSize:12)),const SizedBox(height:20),AppText(card['points'].toString()+' pts',style:const TextStyle(color:mint,fontWeight:FontWeight.w900,fontSize:34,letterSpacing:-1))])),
 if(onStore!=null)Padding(padding:const EdgeInsets.fromLTRB(12,8,12,0),child:FilledButton.tonalIcon(onPressed:onStore,icon:const Icon(Icons.storefront_outlined),label:const AppText('Voir les offres du commerce'))),
 Padding(padding:const EdgeInsets.symmetric(horizontal:15,vertical:6),child:Row(children:[Expanded(child:AppText(card['eligible'].toString()+' récompense(s) accessible(s)',style:const TextStyle(color:muted,fontSize:12))),TextButton(onPressed:onOpen,child:const AppText('Ouvrir')),IconButton(tooltip:tr('Retirer la carte'),onPressed:onRemove,icon:const Icon(Icons.remove_circle_outline,color:muted))]))
 ])));
}
