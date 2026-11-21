import 'package:flutter/material.dart';
import 'api.dart';
import 'app_language.dart';

class ScanHistoryPage extends StatefulWidget {
 final Api api;const ScanHistoryPage({super.key,required this.api});
 @override State<ScanHistoryPage> createState()=>_ScanHistoryPageState();
}
class _ScanHistoryPageState extends State<ScanHistoryPage>{
 final rows=<dynamic>[];String state='',error='';String? cursor;bool busy=false,offline=false;
 static const labels={'':'Tout','pending':'En attente','approved':'Validé','rejected':'Refusé','expired':'Expiré'};
 @override void initState(){super.initState();load();}
 Future<void> load({bool more=false})async{
  if(busy)return;setState((){busy=true;error='';});final selected=state;
  try{
   final d=await widget.api.cached('/mobile/business/scans?limit=30${state.isEmpty?'':'&state=$state'}${more&&cursor!=null?'&cursor=${Uri.encodeQueryComponent(cursor!)}':''}');
   if(!mounted||state!=selected)return;
   setState((){if(!more)rows.clear();final ids=rows.map((r)=>r['id']).toSet();rows.addAll((d['requests'] as List).where((r)=>!ids.contains(r['id'])));cursor=d['next_cursor'] as String?;offline=d['_cached']==true;});
  }catch(e){if(mounted)setState(()=>error=e.toString());}finally{if(mounted)setState(()=>busy=false);}
 }
 String date(Object? raw){if(raw is! int)return '';final d=DateTime.fromMillisecondsSinceEpoch(raw*1000).toLocal();return '${d.year}-${d.month.toString().padLeft(2,'0')}-${d.day.toString().padLeft(2,'0')} ${d.hour.toString().padLeft(2,'0')}:${d.minute.toString().padLeft(2,'0')}';}
 @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const AppText('Historique des scans'),actions:[IconButton(onPressed:busy?null:()=>load(),tooltip:tr('Actualiser'),icon:const Icon(Icons.refresh))]),body:ListView(padding:const EdgeInsets.all(18),children:[
  Wrap(spacing:8,children:[for(final e in labels.entries)ChoiceChip(label:AppText(e.value),selected:state==e.key,onSelected:busy?null:(_){setState(()=>state=e.key);load();})]),
  if(busy)const LinearProgressIndicator(),if(offline)const AppText('Hors connexion · dernières données enregistrées'),
  if(error.isNotEmpty)...[AppText(error),TextButton(onPressed:busy?null:()=>load(),child:const AppText('Réessayer'))],
  if(!busy&&error.isEmpty&&rows.isEmpty)const Padding(padding:EdgeInsets.all(22),child:AppText('Aucun scan pour ce filtre.')),
  for(final r in rows)Card(child:ListTile(leading:Icon(r['state']=='approved'?Icons.check_circle_outline:r['state']=='rejected'?Icons.cancel_outlined:Icons.schedule),title:AppText(r['name']?.toString()??''),subtitle:AppText('${tr(labels[r['state']]??r['state'].toString())} · ${date(r['decided']??r['created'])}'),trailing:r['state']=='approved'?AppText('+${r['points']} points'):null)),
  if(cursor!=null)OutlinedButton(onPressed:busy?null:()=>load(more:true),child:const AppText('Charger la suite')),
 ]));
}
