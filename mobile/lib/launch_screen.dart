import 'package:flutter/material.dart';
import 'app_language.dart';
import 'premium.dart';

class LaunchScreen extends StatelessWidget {
 final Widget Function() client,business;
 const LaunchScreen({super.key,required this.client,required this.business});
 @override Widget build(BuildContext context)=>Scaffold(backgroundColor:ink,body:SafeArea(child:ListView(padding:const EdgeInsets.all(24),children:[
  Row(children:[Image.asset('assets/tunibiz.png',height:42),const SizedBox(width:12),const AppText('TUNIBIZ',style:TextStyle(color:Colors.white,fontSize:22,fontWeight:FontWeight.w900,letterSpacing:1)),const Spacer()]),
  const SizedBox(height:14),const LanguagePicker(),const SizedBox(height:24),
  ClipRRect(borderRadius:BorderRadius.circular(28),child:Stack(children:[Image.asset('assets/cafe.webp',height:215,width:double.infinity,fit:BoxFit.cover),Positioned.fill(child:DecoratedBox(decoration:BoxDecoration(gradient:LinearGradient(begin:Alignment.topCenter,end:Alignment.bottomCenter,colors:[Colors.transparent,ink.withValues(alpha:.85)])))),const PositionedDirectional(start:20,bottom:18,end:20,child:AppText('Votre fidélité, partout près de vous.',style:TextStyle(color:Colors.white,fontSize:28,fontWeight:FontWeight.w900,height:1.1)))])),
  const SizedBox(height:23),const AppText('Découvrez vos commerces, retrouvez vos points et profitez de leurs avantages.',style:TextStyle(color:Colors.white70,fontSize:16,height:1.6)),const SizedBox(height:24),
  _role(context,'Espace client','Je suis client',Icons.loyalty_outlined,client,mint),const SizedBox(height:13),
  _role(context,'Espace établissement','Je suis commerçant',Icons.storefront_outlined,business,const Color(0xff85aaff)),
  const SizedBox(height:20),const AppText('TUNIBIZ · 0.6.0',textAlign:TextAlign.center,style:TextStyle(color:Colors.white38,fontSize:12)),
 ])));
 Widget _role(BuildContext context,String title,String action,IconData icon,Widget Function() destination,Color color)=>Material(color:Colors.white.withValues(alpha:.08),borderRadius:BorderRadius.circular(21),child:InkWell(borderRadius:BorderRadius.circular(21),onTap:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>destination())),child:Padding(padding:const EdgeInsets.all(20),child:Row(children:[Container(padding:const EdgeInsets.all(12),decoration:BoxDecoration(color:color.withValues(alpha:.13),borderRadius:BorderRadius.circular(15)),child:Icon(icon,color:color,size:28)),const SizedBox(width:16),Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[AppText(title,style:const TextStyle(color:Colors.white,fontSize:19,fontWeight:FontWeight.w800)),AppText(action,style:TextStyle(color:color,fontSize:13))])),const Icon(Icons.arrow_forward,color:Colors.white)]))));
}
