import 'package:flutter/material.dart';
import 'dart:convert';
import 'package:flutter/services.dart';
import 'api.dart';
import 'premium.dart';
const establishmentTypes={'grocery_general':'Alimentation générale','drugstore':'Drugstore','grocery':'Épicerie','coffee':'Café','restaurant':'Restaurant','bakery':'Pâtisserie','shopping':'Shopping','clothing':'Vêtements','other':'Autres'};
String establishmentLabel(Map? shop){
 final k=shop?['category'];
 if(k=='other')return (shop?['category_detail']??'Autres').toString();
 return establishmentTypes[k]??const {'general':'Autres','drinks':'Boissons','beauty':'Beauté'}[k]??'Commerce';
}
class MerchantQrPanel extends StatefulWidget{
 final Api api; final VoidCallback onApprovals;
 const MerchantQrPanel({super.key,required this.api,required this.onApprovals});
 @override State<MerchantQrPanel> createState()=>_MerchantQrPanelState();
}
class _MerchantQrPanelState extends State<MerchantQrPanel>{
 Map<String,dynamic>? qr; String? error;bool busy=false;
 @override void initState(){super.initState();load();}
 Future<void> load()async{
 if(busy)return;setState(()=>busy=true);
 try{final r=await widget.api.call('/crm/store-qr');if(mounted)setState((){qr=r;error=null;});}
 catch(e){if(mounted)setState((){qr=null;error='QR indisponible. Vérifiez votre connexion et l’activation du compte.';});}
 finally{if(mounted)setState(()=>busy=false);}
 }
 @override Widget build(BuildContext context)=>Container(padding:const EdgeInsets.all(18),decoration:BoxDecoration(color:Colors.white,borderRadius:BorderRadius.circular(24),border:Border.all(color:const Color(0xFFE4EBF2))),child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
 const Text('MON QR DE FIDÉLITÉ',style:TextStyle(color:cobalt,fontSize:12,fontWeight:FontWeight.w800,letterSpacing:1)),
 const SizedBox(height:8),Text(qr?['shop']?.toString()??'QR de votre établissement',style:const TextStyle(color:ink,fontSize:22,fontWeight:FontWeight.w800)),
 const Text('À présenter à vos clients en caisse.'),
 if(busy)const LinearProgressIndicator(),
 if(qr!=null)...[
 Center(child:Image.memory(base64Decode(qr!['png'] as String),width:216,height:216,fit:BoxFit.contain,filterQuality:FilterQuality.none)),
 const Text('3 points de bienvenue · achats suivants sur validation',textAlign:TextAlign.center,style:TextStyle(fontSize:12,color:muted)),
 OutlinedButton.icon(onPressed:()=>Clipboard.setData(ClipboardData(text:qr!['url'] as String)),icon:const Icon(Icons.copy),label:const Text('Copier mon lien QR')),
 FilledButton.icon(onPressed:widget.onApprovals,icon:const Icon(Icons.check_circle_outline),label:const Text('Valider les demandes'))
 ],if(error!=null)...[Text(error!,style:const TextStyle(color:Colors.red)),TextButton(onPressed:busy?null:load,child:const Text('Réessayer'))]
 ]));
}
