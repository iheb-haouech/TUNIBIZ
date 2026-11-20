import 'app_language.dart';
import 'dart:convert';
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'api.dart';
import 'checkout_scanner.dart';

String? storeSlug(String value){
 final u=Uri.tryParse(value.trim());
 if(u==null||u.scheme!='https'||u.host!='ihebhaouech.pythonanywhere.com'||u.hasPort||u.userInfo.isNotEmpty||u.pathSegments.length!=2||u.pathSegments.first!='join')return null;
 final s=u.pathSegments.last;return RegExp(r'^[a-zA-Z0-9_-]{1,80}$').hasMatch(s)?s:null;
}
Future<String?> scanStore(BuildContext context)async{
 final value=await Navigator.push<String>(context,MaterialPageRoute(builder:(_)=>CheckoutScanner(accept:(v)=>storeSlug(v)!=null,title:'Scanner le QR du commerce')));
 return value==null?null:storeSlug(value);
}
class StoreApprovals extends StatefulWidget{
 final Api api;
 const StoreApprovals({super.key,required this.api});
 @override State<StoreApprovals> createState()=>_StoreApprovalsState();
}
class _StoreApprovalsState extends State<StoreApprovals>{
 Map<String,dynamic>? qr;List<dynamic> queue=[];bool busy=false;String msg='';
 Timer? poll;bool baseline=false;Set<String> known={};
 @override void initState(){super.initState();refresh();poll=Timer.periodic(const Duration(seconds:15),(_){if(mounted&&WidgetsBinding.instance.lifecycleState==AppLifecycleState.resumed&&ModalRoute.of(context)?.isCurrent==true)refresh(silent:true);});}
 @override void dispose(){poll?.cancel();super.dispose();}
 Future<void> refresh({bool silent=false})async{
 if(busy)return;setState(()=>busy=true);
 try{final q=qr??await widget.api.call('/crm/store-qr'),r=await widget.api.call('/crm/store-scans');if(mounted){final next=r['requests'] as List;final ids=next.map((x)=>x['id'].toString()).toSet();if(baseline&&ids.difference(known).isNotEmpty)ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:AppText('Nouvelle demande QR à valider')));known=ids;baseline=true;setState((){qr=q;queue=next;});}}
 catch(e){if(mounted)setState(()=>msg=e.toString());}finally{if(mounted)setState(()=>busy=false);}
 }
 Future<void> decide(Map r,bool approved)async{
 int points=1;
 if(approved){
 final v=await showDialog<int>(context:context,builder:(ctx){String p='1';return AlertDialog(title:AppText('Valider '+r['name'].toString()),content:TextFormField(initialValue:'1',keyboardType:TextInputType.number,inputFormatters:[FilteringTextInputFormatter.digitsOnly,LengthLimitingTextInputFormatter(4)],onChanged:(v)=>p=v,decoration:const AppInputDecoration(labelText:'Points après achat (1–1000)')),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const AppText('Annuler')),FilledButton(onPressed:(){final n=int.tryParse(p);if(n!=null&&n>=1&&n<=1000)Navigator.pop(ctx,n);},child:const AppText('Confirmer'))]);});
 if(v==null||!mounted)return;points=v;
 }else{final v=await showDialog<bool>(context:context,builder:(ctx)=>AlertDialog(title:const AppText('Refuser cette demande ?'),actions:[TextButton(onPressed:()=>Navigator.pop(ctx,false),child:const AppText('Annuler')),FilledButton(onPressed:()=>Navigator.pop(ctx,true),child:const AppText('Refuser'))]));if(v!=true||!mounted)return;}
 if(busy||!mounted)return;setState(()=>busy=true);
 try{final d=await widget.api.call('/crm/store-scan/decide',{'id':r['id'],'action':approved?'approve':'reject','points':points});if(mounted)setState(()=>msg=approved?'Validé : +'+d['points'].toString()+' points':'Demande refusée');}
 catch(e){if(mounted)setState(()=>msg=e.toString());}finally{if(mounted){setState(()=>busy=false);await refresh();}}
 }
 Future<void> exportQr(bool save)async{if(qr==null)return;try{final ok=await const MethodChannel('tn.tunibiz/private').invokeMethod<bool>(save?'saveQr':'shareQr',{'png':qr!['png'],'title':'TUNIBIZ QR'});if(mounted&&ok==true)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:AppText(save?'QR enregistré.':'QR prêt à partager.')));}catch(_){if(mounted)setState(()=>msg='Impossible d’exporter le QR. Réessayez.');}}
 @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const AppText('QR & validations'),actions:[IconButton(onPressed:busy?null:refresh,icon:const Icon(Icons.refresh))]),body:ListView(padding:const EdgeInsets.all(18),children:[
 if(busy)const LinearProgressIndicator(),if(msg.isNotEmpty)AppText(msg),if(qr!=null)...[
 AppText(qr!['shop'].toString(),style:Theme.of(context).textTheme.headlineSmall),
 const AppText('QR fixe du commerce · 3 points de bienvenue'),
 Center(child:Image.memory(base64Decode(qr!['png']),width:240,height:240)),
 Row(children:[Expanded(child:OutlinedButton.icon(onPressed:busy?null:()=>exportQr(false),icon:const Icon(Icons.share_outlined),label:const AppText('Partager le QR'))),const SizedBox(width:8),Expanded(child:OutlinedButton.icon(onPressed:busy?null:()=>exportQr(true),icon:const Icon(Icons.download_outlined),label:const AppText('Exporter le QR')))]),
 OutlinedButton.icon(onPressed:()=>Clipboard.setData(ClipboardData(text:qr!['url'].toString())),icon:const Icon(Icons.copy),label:const AppText('Copier le lien du commerce')),
 OutlinedButton.icon(onPressed:()=>Clipboard.setData(ClipboardData(text:qr!['download_url'].toString())),icon:const Icon(Icons.download),label:const AppText('Copier le lien général de téléchargement'))],
 const SizedBox(height:18),const AppText('Demandes d’achat',style:TextStyle(fontWeight:FontWeight.bold,fontSize:22)),
 const AppText('Vérifiez l’achat avant validation. Défaut : 1 point, modifiable. Demande valable 5 minutes.'),
 if(queue.isEmpty)const Padding(padding:EdgeInsets.all(16),child:AppText('Aucune demande en attente.')),
 for(final r in queue)Card(child:ListTile(title:AppText(r['name'].toString()),subtitle:const AppText('Achat à confirmer'),trailing:Wrap(children:[IconButton(onPressed:busy?null:()=>decide(r,false),tooltip:tr('Refuser'),icon:const Icon(Icons.close)),IconButton(onPressed:busy?null:()=>decide(r,true),tooltip:tr('Valider'),icon:const Icon(Icons.check_circle))]))),
 FilledButton(onPressed:busy?null:refresh,child:const AppText('Actualiser les demandes'))
 ]));
}
