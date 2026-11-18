import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'premium.dart';

bool validCheckoutToken(String value)=>RegExp(r'^TNB1:[A-Za-z0-9_-]{24}$').hasMatch(value);
class CheckoutScanner extends StatefulWidget{
 const CheckoutScanner({super.key});
 @override State<CheckoutScanner> createState()=>_CheckoutScannerState();
}
class _CheckoutScannerState extends State<CheckoutScanner>{
 final controller=MobileScannerController(formats:[BarcodeFormat.qrCode],detectionSpeed:DetectionSpeed.noDuplicates);
 bool finished=false;
 @override void dispose(){controller.dispose();super.dispose();}
 void detected(BarcodeCapture capture){
 if(finished||!mounted)return;
 for(final b in capture.barcodes){final v=b.rawValue;if(v!=null&&validCheckoutToken(v)){finished=true;Navigator.pop(context,v);return;}}
 }
 @override Widget build(BuildContext context)=>Scaffold(backgroundColor:ink,appBar:AppBar(title:const Text('Scanner la carte client')),body:SafeArea(child:Column(children:[
 const Padding(padding:EdgeInsets.all(16),child:Text('Placez le QR temporaire dans le cadre. La caméra ne sert qu’à lire le code.',textAlign:TextAlign.center,style:TextStyle(color:Colors.white))),
 Expanded(child:Padding(padding:const EdgeInsets.all(18),child:ClipRRect(borderRadius:BorderRadius.circular(22),child:MobileScanner(controller:controller,onDetect:detected)))),
 Padding(padding:const EdgeInsets.all(18),child:FilledButton(onPressed:()=>Navigator.pop(context),child:const Text('Annuler / saisir le code manuellement')))
 ])));
}
