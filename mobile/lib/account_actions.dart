import 'package:flutter/material.dart';
import 'api.dart';
import 'app_language.dart';

/// Only an opaque token or the exact HTTPS link sent by TUNIBIZ is accepted.
String? accountActionToken(String input, String path) {
 final value=input.trim(), pattern=RegExp(r'^[A-Za-z0-9_-]{43}$');
 if(pattern.hasMatch(value))return value;
 final url=Uri.tryParse(value);
 if(url==null||url.scheme!='https'||url.host!='ihebhaouech.pythonanywhere.com'||url.hasPort||url.userInfo.isNotEmpty||url.hasFragment||url.path!=path||url.queryParametersAll.length!=1||url.queryParametersAll['token']?.length!=1)return null;
 final token=url.queryParameters['token'];return token!=null&&pattern.hasMatch(token)?token:null;
}
class EmailVerificationPage extends StatefulWidget {
 final Api api;const EmailVerificationPage({super.key,required this.api});
 @override State<EmailVerificationPage> createState()=>_EmailVerificationPageState();
}
class _EmailVerificationPageState extends State<EmailVerificationPage> with WidgetsBindingObserver {
 final link=TextEditingController();bool busy=false,verified=false,delivery=false;String message='';
 @override void initState(){super.initState();WidgetsBinding.instance.addObserver(this);status();}
 @override void dispose(){WidgetsBinding.instance.removeObserver(this);link.dispose();super.dispose();}
 @override void didChangeAppLifecycleState(AppLifecycleState state){if(state==AppLifecycleState.resumed&&!busy)status();}
 Future<void> run(Future<void> Function() work)async{
  if(busy)return;setState((){busy=true;message='';});
  try{await work();}catch(e){if(mounted)setState(()=>message=e.toString().replaceFirst('Exception: ',''));}
  finally{if(mounted)setState(()=>busy=false);}
 }
 Future<void> readStatus()async{final d=await widget.api.call('/verification/status');if(mounted)setState((){verified=d['verified']==true;delivery=d['delivery_enabled']==true;});}
 Future<void> status()=>run(readStatus);
 Future<void> request()=>run(()async{
  if(widget.api.csrf.isEmpty)await widget.api.init();final d=await widget.api.call('/verification/request',{});
  if(mounted)setState(()=>message=d['message']?.toString()??'Consultez votre boîte e-mail.');await readStatus();
 });
 Future<void> confirm()async{
  final token=accountActionToken(link.text,'/verify-email');
  if(token==null){setState(()=>message='Collez le lien de confirmation TUNIBIZ reçu par e-mail.');return;}
  await run(()async{
   if(widget.api.csrf.isEmpty)await widget.api.init();await widget.api.call('/verification/confirm',{'token':token});await readStatus();
   if(!mounted)return;link.clear();setState(()=>message=verified?'':'Le lien a été traité. Vérifiez le compte connecté.');
  });
 }
 @override Widget build(BuildContext context)=>PopScope(canPop:!busy,child:Scaffold(appBar:AppBar(title:const AppText('Vérifier mon email')),body:ListView(padding:const EdgeInsets.all(22),children:[
  if(busy)const LinearProgressIndicator(),Icon(verified?Icons.verified_user_outlined:Icons.mark_email_read_outlined,size:64),const SizedBox(height:20),
  AppText(verified?'Adresse e-mail confirmée':'Confirmez votre adresse e-mail',style:const TextStyle(fontSize:26,fontWeight:FontWeight.w800)),const SizedBox(height:14),
  if(message.isNotEmpty)Padding(padding:const EdgeInsets.only(bottom:14),child:AppText(message)),
  if(verified)FilledButton(onPressed:busy?null:()=>Navigator.pop(context,true),child:const AppText('Retour à mon compte')) else ...[
   const AppText('Ouvrez votre e-mail TUNIBIZ ou collez son lien de confirmation ici.'),const SizedBox(height:18),
   FilledButton.icon(onPressed:busy||!delivery?null:request,icon:const Icon(Icons.send_outlined),label:const AppText('Envoyer un lien de confirmation')),
   if(!delivery)const AppText('Envoi des e-mails temporairement indisponible.'),const SizedBox(height:22),
   TextField(controller:link,autocorrect:false,enableSuggestions:false,decoration:const AppInputDecoration(labelText:'Lien de confirmation',prefixIcon:Icon(Icons.link))),const SizedBox(height:14),
   FilledButton(onPressed:busy?null:confirm,child:const AppText('Confirmer mon adresse')),
   TextButton(onPressed:busy?null:status,child:const AppText('Actualiser la confirmation')),
  ],
 ])));
}
