import 'package:flutter/material.dart';
import 'account_actions.dart';
import 'app_language.dart';
import 'api.dart';

Future<void> recoverPassword(BuildContext context,String kind,String initialEmail,{Api? sourceApi})async{
 final changed=await Navigator.push<bool>(context,MaterialPageRoute(builder:(_)=>PasswordRecoveryPage(kind:kind,initialEmail:initialEmail,serverUrl:sourceApi?.serverUrl)));
 if(changed==true&&sourceApi!=null)await sourceApi.clearLocal();
}
class PasswordRecoveryPage extends StatefulWidget {
 final String kind,initialEmail;final String? serverUrl;final Api? apiOverride;
 const PasswordRecoveryPage({super.key,required this.kind,this.initialEmail='',this.serverUrl,this.apiOverride});
 @override State<PasswordRecoveryPage> createState()=>_PasswordRecoveryPageState();
}
class _PasswordRecoveryPageState extends State<PasswordRecoveryPage>{
 late final api=widget.apiOverride??Api(serverUrl:widget.serverUrl);
 late final email=TextEditingController(text:widget.initialEmail);
 final link=TextEditingController(),password=TextEditingController(),confirmation=TextEditingController();
 bool busy=false,changed=false;String message='';
 @override void dispose(){email.dispose();link.dispose();password.dispose();confirmation.dispose();if(widget.apiOverride==null)api.close();super.dispose();}
 Future<void> showMessage(String value)async{if(!mounted)return;setState(()=>message=value);ScaffoldMessenger.of(context).clearSnackBars();ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:AppText(value)));}
 Future<void> run(Future<void> Function() work)async{
  if(busy)return;FocusManager.instance.primaryFocus?.unfocus();setState((){busy=true;message='';});
  try{if(api.csrf.isEmpty)await api.init();await work();}catch(e){await showMessage(e.toString().replaceFirst('Exception: ',''));}finally{if(mounted)setState(()=>busy=false);}
 }
 Future<void> request()async{
  if(!RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(email.text.trim())||!['consumer','merchant'].contains(widget.kind)){await showMessage('Vérifiez votre adresse e-mail.');return;}
  await run(()async{final d=await api.call('/password/request',{'kind':widget.kind,'email':email.text.trim()});if(mounted)setState(()=>message=d['message']?.toString()??'Consultez votre boîte e-mail.');});
 }
 Future<void> reset()async{
  final token=accountActionToken(link.text,'/reset-password');
  if(token==null){await showMessage('Collez le lien de réinitialisation TUNIBIZ reçu par e-mail.');return;}
  if(password.text.length<12||password.text.length>128){await showMessage('Choisissez un mot de passe de 12 à 128 caractères.');return;}
  if(password.text!=confirmation.text){await showMessage('Les deux mots de passe doivent être identiques.');return;}
  await run(()async{await api.call('/password/reset',{'token':token,'password':password.text});if(!mounted)return;link.clear();password.clear();confirmation.clear();setState((){changed=true;message='';});});
 }
 @override Widget build(BuildContext context)=>PopScope(canPop:!busy,child:Scaffold(appBar:AppBar(title:const AppText('Récupération de compte')),body:ListView(padding:const EdgeInsets.all(22),children:[
  if(busy)const LinearProgressIndicator(),Icon(changed?Icons.lock_reset:Icons.lock_outline,size:64),const SizedBox(height:18),
  AppText(changed?'Mot de passe modifié':'Retrouvez votre compte',style:const TextStyle(fontSize:26,fontWeight:FontWeight.w800)),const SizedBox(height:14),
  if(message.isNotEmpty)Padding(padding:const EdgeInsets.only(bottom:14),child:AppText(message)),
  if(changed)...[const AppText('Connectez-vous avec votre nouveau mot de passe.'),const SizedBox(height:18),FilledButton(onPressed:()=>Navigator.pop(context,true),child:const AppText('Retour à la connexion'))]else ...[
   const AppText('Pour un compte Google, utilisez la récupération de votre compte Google.'),const SizedBox(height:18),
   TextField(controller:email,keyboardType:TextInputType.emailAddress,autocorrect:false,decoration:const AppInputDecoration(labelText:'Email')),const SizedBox(height:12),
   FilledButton.icon(onPressed:busy?null:request,icon:const Icon(Icons.mail_outline),label:const AppText('Recevoir un lien de réinitialisation')),const SizedBox(height:28),
   const AppText('Vous avez déjà reçu le lien ?',style:TextStyle(fontSize:19,fontWeight:FontWeight.w700)),const SizedBox(height:12),
   TextField(controller:link,autocorrect:false,enableSuggestions:false,decoration:const AppInputDecoration(labelText:'Lien de réinitialisation')),const SizedBox(height:12),
   TextField(controller:password,obscureText:true,autocorrect:false,enableSuggestions:false,maxLength:128,decoration:const AppInputDecoration(labelText:'Nouveau mot de passe')),const SizedBox(height:12),
   TextField(controller:confirmation,obscureText:true,autocorrect:false,enableSuggestions:false,maxLength:128,decoration:const AppInputDecoration(labelText:'Répéter le mot de passe')),const SizedBox(height:16),
   FilledButton(onPressed:busy?null:reset,child:const AppText('Enregistrer le nouveau mot de passe')),
  ],
 ])));
}
