import 'app_language.dart';
import 'dart:math' as math;
import 'package:flutter/material.dart';

const ink=Color(0xFF071321), mint=Color(0xFF2DD4BF), cobalt=Color(0xFF2563EB), paper=Color(0xFFF8FAFC);
const muted=Color(0xFF718096);
class PremiumRing extends StatelessWidget {
 final int points,goal; final bool signedIn;
 const PremiumRing({super.key,required this.points,required this.goal,this.signedIn=true});
 @override Widget build(BuildContext context)=>SizedBox(width:226,height:226,child:Stack(alignment:Alignment.center,children:[
  Positioned.fill(child:CustomPaint(painter:_RingPainter(signedIn?(points/math.max(1,goal)).clamp(0,1).toDouble():0))),
  Column(mainAxisSize:MainAxisSize.min,children:[
   AppText(signedIn?points.toString():'—',style:const TextStyle(fontSize:52,color:Colors.white,fontWeight:FontWeight.w800,letterSpacing:-2)),
   const AppText('POINTS',style:TextStyle(color:mint,fontSize:11,fontWeight:FontWeight.w700,letterSpacing:3)),
   const SizedBox(height:8),AppText(signedIn?'Objectif '+goal.toString():'Votre fidélité',style:const TextStyle(color:Colors.white60,fontSize:12))
  ])
 ]));
}
class _RingPainter extends CustomPainter {
 final double progress;_RingPainter(this.progress);
 @override void paint(Canvas c,Size s){
  final center=s.center(Offset.zero),r=s.width/2-18,arc=Rect.fromCircle(center:center,radius:r);
  const start=math.pi*.75,sweep=math.pi*1.5;
  c.drawCircle(center,r-17,Paint()..shader=RadialGradient(colors:[const Color(0xFF132D45),ink]).createShader(arc));
  c.drawArc(arc,start,sweep,false,Paint()..style=PaintingStyle.stroke..strokeWidth=4..strokeCap=StrokeCap.round..color=const Color(0xFF31465A));
  if(progress>0){
   c.drawArc(arc,start,sweep*progress,false,Paint()..style=PaintingStyle.stroke..strokeWidth=11..strokeCap=StrokeCap.round..color=mint.withValues(alpha:.25)..maskFilter=const MaskFilter.blur(BlurStyle.normal,8));
   c.drawArc(arc,start,sweep*progress,false,Paint()..style=PaintingStyle.stroke..strokeWidth=5..strokeCap=StrokeCap.round..shader=const SweepGradient(colors:[cobalt,mint,cobalt]).createShader(arc));
  }
  for(int i=0;i<=36;i++){final a=start+sweep*i/36;final outer=center+Offset(math.cos(a),math.sin(a))*(r+8);final inner=center+Offset(math.cos(a),math.sin(a))*(r+5);c.drawLine(inner,outer,Paint()..color=Colors.white24..strokeWidth=1);}
  final end=center+Offset(math.cos(start+sweep*progress),math.sin(start+sweep*progress))*r;
  c.drawCircle(end,4,Paint()..color=mint);
 }
 @override bool shouldRepaint(covariant _RingPainter old)=>old.progress!=progress;
}
class PremiumHero extends StatelessWidget{
 final String name,shop,description,action;final int points,goal;final bool signedIn;final VoidCallback onAction;
 const PremiumHero({super.key,required this.name,required this.shop,required this.description,required this.action,required this.points,required this.goal,required this.signedIn,required this.onAction});
 @override Widget build(BuildContext context)=>Container(width:double.infinity,decoration:const BoxDecoration(gradient:LinearGradient(begin:Alignment.topLeft,end:Alignment.bottomRight,colors:[ink,Color(0xFF10263C),ink])),child:Stack(children:[
  Positioned.fill(child:CustomPaint(painter:_Pattern())),
  Padding(padding:const EdgeInsets.fromLTRB(24,18,24,28),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
   Row(children:[Container(width:38,height:38,decoration:BoxDecoration(color:cobalt,borderRadius:BorderRadius.circular(12)),alignment:Alignment.center,child:const AppText('T.',style:TextStyle(fontWeight:FontWeight.w900,fontSize:23,color:Colors.white))),const SizedBox(width:10),const AppText('TUNIBIZ',style:TextStyle(color:Colors.white,fontSize:18,fontWeight:FontWeight.w800,letterSpacing:2)),const Spacer(),const Icon(Icons.auto_awesome_outlined,color:mint)]),
   const SizedBox(height:23),const AppText('VOTRE UNIVERS DE FIDÉLITÉ',style:TextStyle(color:mint,fontSize:10,letterSpacing:2,fontWeight:FontWeight.w700)),
   const SizedBox(height:7),AppText(name,style:const TextStyle(color:Colors.white,fontSize:32,fontWeight:FontWeight.w800,letterSpacing:-1)),
   AppText(shop,style:const TextStyle(color:Colors.white60,fontSize:13)),const SizedBox(height:9),
   Center(child:PremiumRing(points:points,goal:goal,signedIn:signedIn)),
   Center(child:AppText(description,textAlign:TextAlign.center,style:const TextStyle(color:Colors.white70,fontSize:14,height:1.5))),
   const SizedBox(height:19),Center(child:FilledButton(onPressed:onAction,style:FilledButton.styleFrom(backgroundColor:mint,foregroundColor:ink,padding:const EdgeInsets.symmetric(horizontal:28,vertical:15)),child:AppText(action,style:const TextStyle(fontWeight:FontWeight.w800))))
  ]))
 ]));
}
class _Pattern extends CustomPainter{
 @override void paint(Canvas c,Size s){final p=Paint()..color=const Color(0xFF2DD4BF).withValues(alpha:.045)..style=PaintingStyle.stroke;for(double y=115;y<s.height-70;y+=22){for(double x=-20;x<s.width+20;x+=26){final path=Path()..moveTo(x,y-6)..lineTo(x+8,y)..lineTo(x,y+6)..lineTo(x-8,y)..close();c.drawPath(path,p);}}}
 @override bool shouldRepaint(covariant CustomPainter old)=>false;
}
class FeatureTile extends StatelessWidget {
 final String asset,title,subtitle,tag;final VoidCallback onTap;
 const FeatureTile({super.key,required this.asset,required this.title,required this.subtitle,required this.tag,required this.onTap});
 @override Widget build(BuildContext context)=>Material(color:Colors.white,borderRadius:BorderRadius.circular(20),clipBehavior:Clip.antiAlias,child:InkWell(onTap:onTap,child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
  SizedBox(height:156,width:double.infinity,child:Stack(fit:StackFit.expand,children:[
   Image.asset(asset,fit:BoxFit.cover,errorBuilder:(_,__,___)=>Container(color:ink,child:const Icon(Icons.card_giftcard,color:mint,size:48))),
   Positioned(left:12,top:12,child:Container(padding:const EdgeInsets.symmetric(horizontal:11,vertical:7),decoration:BoxDecoration(color:ink,borderRadius:BorderRadius.circular(30)),child:AppText(tag,style:const TextStyle(color:Colors.white,fontSize:11,fontWeight:FontWeight.bold))))
  ])),
  Padding(padding:const EdgeInsets.all(16),child:Row(children:[Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[AppText(title,style:const TextStyle(color:ink,fontWeight:FontWeight.w800,fontSize:18)),const SizedBox(height:5),AppText(subtitle,style:const TextStyle(color:muted,fontSize:13,height:1.4))])),const SizedBox(width:12),const Icon(Icons.arrow_forward_rounded,color:cobalt)]))
 ])));
}
class PremiumNav extends StatelessWidget{
 final int index;final ValueChanged<int> onSelected;
 const PremiumNav({super.key,required this.index,required this.onSelected});
 @override Widget build(BuildContext context)=>NavigationBar(backgroundColor:Colors.white,indicatorColor:const Color(0xFFE1F9F5),selectedIndex:index,onDestinationSelected:onSelected,destinations:const [
  AppNavigationDestination(icon:Icon(Icons.home_outlined),selectedIcon:Icon(Icons.home_rounded,color:ink),label:'Accueil'),
  AppNavigationDestination(icon:Icon(Icons.card_giftcard_outlined),label:'Fidélité'),
  AppNavigationDestination(icon:Icon(Icons.radar),label:'Nearby'),
  AppNavigationDestination(icon:Icon(Icons.storefront_outlined),label:'Business')
 ]);
}
