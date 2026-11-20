import 'app_language.dart';
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
 @override Widget build(BuildContext context)=>Scaffold(backgroundColor:ink,appBar:AppBar(title:AppText(widget.title)),body:SafeArea(child:Column(children:[
 const Padding(padding:EdgeInsets.all(16),child:AppText('Placez le QR dans le cadre. La caméra ne sert qu’à lire le code.',textAlign:TextAlign.center,style:TextStyle(color:Colors.white))),
 Expanded(child:Padding(padding:const EdgeInsets.all(18),child:ClipRRect(borderRadius:BorderRadius.circular(22),child:MobileScanner(controller:controller,onDetect:detected)))),
 Padding(padding:const EdgeInsets.all(18),child:FilledButton(onPressed:()=>Navigator.pop(context),child:const AppText('Annuler / saisir le code manuellement')))
 ])));
}
