import 'app_language.dart';
import 'package:flutter/services.dart';
import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'premium.dart';

bool validCheckoutToken(String value)=>RegExp(r'^TNB1:[A-Za-z0-9_-]{24}$').hasMatch(value);
class CheckoutScanner extends StatefulWidget{
 final bool Function(String)? accept;final String title;
 const CheckoutScanner({super.key,this.accept,this.title='Scanner la carte client'});
 @override State<CheckoutScanner> createState()=>_CheckoutScannerState();
}
class _CheckoutScannerState extends State<CheckoutScanner>{
 final controller=MobileScannerController(formats:[BarcodeFormat.qrCode],detectionSpeed:DetectionSpeed.noDuplicates);
 bool finished=false;
 @override void dispose(){controller.dispose();super.dispose();}
 void detected(BarcodeCapture capture){
 if(finished||!mounted)return;
 for(final b in capture.barcodes){final v=b.rawValue;if(v!=null&&(widget.accept??validCheckoutToken)(v)){finished=true;Navigator.pop(context,v);return;}}
 }
 Future<void> analyzePath(String path)async{try{final result=await controller.analyzeImage(path,formats:[BarcodeFormat.qrCode]);if(result!=null){detected(result);}else if(mounted){ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:AppText('Aucun QR valide dans cette image.')));}}catch(_){if(mounted)ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:AppText('Lecture de l’image indisponible.')));}}
 Future<void> importImage()async{try{final raw=await const MethodChannel('tn.tunibiz/photo').invokeMethod<String>('pick');if(raw==null||!mounted)return;final path=await const MethodChannel('tn.tunibiz/private').invokeMethod<String>('prepareQrImage',{'image':raw});if(path!=null&&mounted)await analyzePath(path);}catch(_){if(mounted)ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:AppText('Lecture de l’image indisponible.')));}}
 Future<void> manual()async{String value='';String? error;final result=await showDialog<String>(context:context,builder:(ctx)=>StatefulBuilder(builder:(ctx,update)=>AlertDialog(title:const AppText('Saisir un lien ou code QR'),content:TextField(autofocus:true,onChanged:(text)=>value=text,decoration:AppInputDecoration(labelText:'Code ou lien QR',errorText:error)),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const AppText('Annuler')),FilledButton(onPressed:(){final text=value.trim();if(!(widget.accept??validCheckoutToken)(text)){update(()=>error='QR TUNIBIZ invalide.');return;}Navigator.pop(ctx,text);},child:const AppText('Confirmer'))])));if(result!=null&&mounted&&!finished){finished=true;Navigator.pop(context,result);}}
 @override Widget build(BuildContext context)=>Scaffold(backgroundColor:ink,appBar:AppBar(title:AppText(widget.title),actions:[IconButton(tooltip:tr('Lire un QR depuis une image'),onPressed:importImage,icon:const Icon(Icons.image_search))]),body:SafeArea(child:Column(children:[
 const Padding(padding:EdgeInsets.all(16),child:AppText('Placez le QR dans le cadre. La caméra ne sert qu’à lire le code.',textAlign:TextAlign.center,style:TextStyle(color:Colors.white))),
 Expanded(child:Padding(padding:const EdgeInsets.all(18),child:ClipRRect(borderRadius:BorderRadius.circular(22),child:MobileScanner(controller:controller,onDetect:detected)))),
 Padding(padding:const EdgeInsets.all(18),child:Wrap(spacing:12,children:[OutlinedButton(onPressed:()=>Navigator.pop(context),child:const AppText('Annuler')),FilledButton(onPressed:manual,child:const AppText('Saisir un lien ou code QR'))]))
 ])));
}
