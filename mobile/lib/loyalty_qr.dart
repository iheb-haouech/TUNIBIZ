import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'api.dart';
import 'premium.dart';

class LoyaltyQr extends StatefulWidget {
 final Api api; final String shop;
 const LoyaltyQr({super.key,required this.api,required this.shop});
 @override State<LoyaltyQr> createState()=>_LoyaltyQrState();
}
class _LoyaltyQrState extends State<LoyaltyQr>{
 Timer? timer; Map<String,dynamic>? pass; DateTime? expiry; bool loading=false; String error='';
 int get remaining=>expiry==null?0:(expiry!.difference(DateTime.now()).inSeconds+1).clamp(0,90).toInt();
 @override void initState(){super.initState();refresh();timer=Timer.periodic(const Duration(seconds:1),(_){if(mounted)setState((){});});}
 @override void dispose(){timer?.cancel();super.dispose();}
 Future<void> refresh()async{
 if(loading)return;setState((){loading=true;pass=null;error='';expiry=null;});
 try{final d=await widget.api.call('/loyalty/qr',{});if(mounted)setState((){pass=d;expiry=DateTime.now().add(Duration(seconds:d['expires_in'] as int));});}
 catch(e){if(mounted)setState(()=>error='Impossible de générer le code. Vérifiez votre connexion.');}
 finally{if(mounted)setState(()=>loading=false);}
 }
 @override Widget build(BuildContext context){final valid=pass!=null&&remaining>0;return Scaffold(backgroundColor:ink,appBar:AppBar(backgroundColor:ink,foregroundColor:Colors.white,title:const Text('Ma carte sécurisée')),body:SafeArea(child:ListView(padding:const EdgeInsets.all(24),children:[
 Text(widget.shop,textAlign:TextAlign.center,style:const TextStyle(color:mint,fontSize:14,fontWeight:FontWeight.w700,letterSpacing:1)),
 const SizedBox(height:20),const Text('Présentez votre carte',textAlign:TextAlign.center,style:TextStyle(color:Colors.white,fontSize:29,fontWeight:FontWeight.w800)),
 const SizedBox(height:10),const Text('Identification en caisse uniquement. Aucun mot de passe ni donnée personnelle dans ce QR.',textAlign:TextAlign.center,style:TextStyle(color:Colors.white70)),
 const SizedBox(height:28),
 Center(child:Container(width:246,height:246,padding:const EdgeInsets.all(8),decoration:BoxDecoration(color:Colors.white,borderRadius:BorderRadius.circular(18),boxShadow:[BoxShadow(color:mint.withValues(alpha:.2),blurRadius:28)]),child:loading?const Center(child:CircularProgressIndicator()):valid?CustomPaint(painter:QrMatrixPainter((pass!['matrix'] as List).map((r)=>(r as List).cast<bool>()).toList())):const Center(child:Icon(Icons.qr_code_2,size:78,color:muted)))),
 const SizedBox(height:20),
 Text(valid?'Expire dans '+remaining.toString()+' s':loading?'Génération en cours…':'Code indisponible ou expiré',textAlign:TextAlign.center,style:const TextStyle(color:mint,fontWeight:FontWeight.w700)),
 if(valid)...[const SizedBox(height:12),LinearProgressIndicator(value:remaining/90,backgroundColor:Colors.white12,color:mint),const SizedBox(height:12),OutlinedButton.icon(onPressed:()async{await Clipboard.setData(ClipboardData(text:pass!['token']));if(context.mounted)ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('Code temporaire copié')));},icon:const Icon(Icons.copy,color:mint),label:const Text('Copier le code temporaire',style:TextStyle(color:mint)))],
 if(error.isNotEmpty)Text(error,textAlign:TextAlign.center,style:const TextStyle(color:Colors.white70)),
 const SizedBox(height:18),FilledButton(onPressed:loading?null:refresh,style:FilledButton.styleFrom(backgroundColor:mint,foregroundColor:ink),child:const Text('Générer un nouveau code')),
 const SizedBox(height:16),const Text('Chaque code est valable 90 secondes et utilisable une seule fois, dans le commerce de votre carte.',textAlign:TextAlign.center,style:TextStyle(color:Colors.white54,fontSize:12))
 ])));}
}
class QrMatrixPainter extends CustomPainter{
 final List<List<bool>> matrix;QrMatrixPainter(this.matrix);
 @override void paint(Canvas c,Size size){if(matrix.isEmpty)return;final n=matrix.length,step=(size.shortestSide/n).floorToDouble();if(step<=0)return;final left=(size.width-n*step)/2,top=(size.height-n*step)/2;final p=Paint()..color=Colors.black..isAntiAlias=false;
 for(var y=0;y<n;y++){for(var x=0;x<n;x++){if(matrix[y][x])c.drawRect(Rect.fromLTWH(left+x*step,top+y*step,step,step),p);}}}
 @override bool shouldRepaint(covariant QrMatrixPainter old)=>old.matrix!=matrix;
}
