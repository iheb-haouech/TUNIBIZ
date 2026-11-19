import 'dart:convert';
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
 @override void initState(){super.initState();refresh();}
 Future<void> refresh()async{
 if(busy)return;setState(()=>busy=true);
 try{final q=await widget.api.call('/crm/store-qr'),r=await widget.api.call('/crm/store-scans');if(mounted)setState((){qr=q;queue=r['requests'] as List;});}
 catch(e){if(mounted)setState(()=>msg=e.toString());}finally{if(mounted)setState(()=>busy=false);}
 }
 Future<void> decide(Map r,bool approved)async{
 int points=1;
 if(approved){
 final v=await showDialog<int>(context:context,builder:(ctx){String p='1';return AlertDialog(title:Text('Valider '+r['name'].toString()),content:TextFormField(initialValue:'1',keyboardType:TextInputType.number,inputFormatters:[FilteringTextInputFormatter.digitsOnly,LengthLimitingTextInputFormatter(4)],onChanged:(v)=>p=v,decoration:const InputDecoration(labelText:'Points après achat (1–1000)')),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('Annuler')),FilledButton(onPressed:(){final n=int.tryParse(p);if(n!=null&&n>=1&&n<=1000)Navigator.pop(ctx,n);},child:const Text('Confirmer'))]);});
 if(v==null||!mounted)return;points=v;
 }else{final v=await showDialog<bool>(context:context,builder:(ctx)=>AlertDialog(title:const Text('Refuser cette demande ?'),actions:[TextButton(onPressed:()=>Navigator.pop(ctx,false),child:const Text('Annuler')),FilledButton(onPressed:()=>Navigator.pop(ctx,true),child:const Text('Refuser'))]));if(v!=true||!mounted)return;}
 if(busy||!mounted)return;setState(()=>busy=true);
 try{final d=await widget.api.call('/crm/store-scan/decide',{'id':r['id'],'action':approved?'approve':'reject','points':points});if(mounted)setState(()=>msg=approved?'Validé : +'+d['points'].toString()+' points':'Demande refusée');}
 catch(e){if(mounted)setState(()=>msg=e.toString());}finally{if(mounted){setState(()=>busy=false);await refresh();}}
 }
 @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const Text('QR & validations'),actions:[IconButton(onPressed:busy?null:refresh,icon:const Icon(Icons.refresh))]),body:ListView(padding:const EdgeInsets.all(18),children:[
 if(busy)const LinearProgressIndicator(),if(msg.isNotEmpty)Text(msg),if(qr!=null)...[
 Text(qr!['shop'].toString(),style:Theme.of(context).textTheme.headlineSmall),
 const Text('QR fixe du commerce · 3 points de bienvenue'),
 Center(child:Image.memory(base64Decode(qr!['png']),width:240,height:240)),
 OutlinedButton.icon(onPressed:()=>Clipboard.setData(ClipboardData(text:qr!['url'].toString())),icon:const Icon(Icons.copy),label:const Text('Copier le lien du commerce')),
 OutlinedButton.icon(onPressed:()=>Clipboard.setData(ClipboardData(text:qr!['download_url'].toString())),icon:const Icon(Icons.download),label:const Text('Copier le lien général de téléchargement'))],
 const SizedBox(height:18),const Text('Demandes d’achat',style:TextStyle(fontWeight:FontWeight.bold,fontSize:22)),
 const Text('Vérifiez l’achat avant validation. Défaut : 1 point, modifiable. Demande valable 5 minutes.'),
 if(queue.isEmpty)const Padding(padding:EdgeInsets.all(16),child:Text('Aucune demande en attente.')),
 for(final r in queue)Card(child:ListTile(title:Text(r['name'].toString()),subtitle:const Text('Achat à confirmer'),trailing:Wrap(children:[IconButton(onPressed:busy?null:()=>decide(r,false),tooltip:'Refuser',icon:const Icon(Icons.close)),IconButton(onPressed:busy?null:()=>decide(r,true),tooltip:'Valider',icon:const Icon(Icons.check_circle))]))),
 FilledButton(onPressed:busy?null:refresh,child:const Text('Actualiser les demandes'))
 ]));
}
