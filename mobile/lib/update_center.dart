import 'app_language.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'api.dart';
const currentVersion='0.6.0';
const currentVersionCode=61;
bool validRelease(Map<String,dynamic> r){
 final v=r['version'],code=r['code'],url=r['url'],sha=r['sha256'];
 return v is String&&RegExp(r'^\d{1,3}\.\d{1,3}\.\d{1,3}$').hasMatch(v)&&code is int&&code>currentVersionCode&&sha is String&&RegExp(r'^[a-fA-F0-9]{64}$').hasMatch(sha)&&(url=='https://github.com/iheb-haouech/TUNIBIZ/releases/download/v'+v+'/TUNIBIZ-v'+v+'.apk'||url=='https://github.com/iheb-haouech/TUNIBIZ/releases/download/v'+v+'/TUNIBIZ-v'+v+'-universal.apk');
}
class UpdateCenter extends StatefulWidget{
 const UpdateCenter({super.key});
 @override State<UpdateCenter> createState()=>_UpdateCenterState();
}
class _UpdateCenterState extends State<UpdateCenter>{
 Map<String,dynamic>? release;String status='Recherche de mise à jour…';bool busy=false;
 @override void initState(){super.initState();check();}
 Future<void> check()async{
 if(busy)return;setState(()=>busy=true);final a=Api();
 try{final d=await a.call('/app/version');final r=d['release'];if(!mounted)return;setState((){release=r is Map<String,dynamic>&&validRelease(r)?r:null;status=release==null?'Aucune nouvelle version publiée':'Nouvelle version disponible';});}
 catch(_){if(mounted)setState(()=>status='Vérification indisponible. Réessayez.');}finally{a.close();if(mounted)setState(()=>busy=false);}
 }
 @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const AppText('Mises à jour TUNIBIZ')),body:ListView(padding:const EdgeInsets.all(20),children:[
 AppText('Version '+currentVersion,style:Theme.of(context).textTheme.headlineSmall),const SizedBox(height:16),AppText(status),if(busy)const LinearProgressIndicator(),
 if(release!=null)...[AppText('Version '+release!['version'].toString()),AppText(release!['notes'].toString()),const SizedBox(height:12),
 FilledButton.icon(onPressed:()async{try{await const MethodChannel('tn.tunibiz/private').invokeMethod('openRelease',{'url':release!['url']});}catch(_){if(mounted)setState(()=>status='Impossible d’ouvrir le lien.');}},icon:const Icon(Icons.download),label:const AppText('Télécharger la mise à jour')),
 const AppText('Android vérifie la signature lors de l’installation. Vérifiez l’empreinte du fichier si nécessaire.'),
 SelectableText('SHA-256 : '+release!['sha256'].toString())],
 OutlinedButton(onPressed:busy?null:check,child:const AppText('Vérifier les mises à jour'))]));
}

class UpdateEntry extends StatefulWidget{
 const UpdateEntry({super.key});
 @override State<UpdateEntry> createState()=>_UpdateEntryState();
}
class _UpdateEntryState extends State<UpdateEntry>{
 bool available=false;
 @override void initState(){super.initState();if(baseUrl.startsWith('https://'))check();}
 Future<void> check()async{final a=Api();try{final d=await a.call('/app/version');final r=d['release'];if(mounted)setState(()=>available=r is Map<String,dynamic>&&validRelease(r));}catch(_){}finally{a.close();}}
 @override Widget build(BuildContext context)=>OutlinedButton.icon(onPressed:()async{await Navigator.push(context,MaterialPageRoute(builder:(_)=>const UpdateCenter()));if(mounted&&baseUrl.startsWith('https://'))await check();},icon:Icon(available?Icons.system_update_alt:Icons.system_update),label:AppText(available?'Nouvelle version disponible':'Mises à jour TUNIBIZ'));
}
