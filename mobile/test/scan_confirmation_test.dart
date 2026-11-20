import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import '../lib/scan_confirmation.dart';

void main(){
 testWidgets('Credited welcome points appear before one Facebook opening',(tester)async{
  final calls=<String>[];
  await tester.pumpWidget(MaterialApp(home:Scaffold(body:ScanConfirmation(shop:'Commerce TEST',result:const {'status':'welcome','points':3,'facebook_url':'https://www.facebook.com/qa-shop'},openFacebook:(url)async{calls.add(url);})))) ;
  expect(find.text('+3 points de bienvenue crédités'),findsOneWidget);
  await tester.pump(const Duration(seconds:2));expect(calls,isEmpty);
  await tester.pump(const Duration(seconds:1));await tester.pump();expect(calls,['https://www.facebook.com/qa-shop']);
  await tester.pump(const Duration(seconds:10));expect(calls,hasLength(1));
 });
 testWidgets('Dismissal cancels Facebook opening and pending never claims credited points',(tester)async{
  var calls=0;
  await tester.pumpWidget(MaterialApp(home:Builder(builder:(context)=>Scaffold(body:FilledButton(onPressed:()=>showScanConfirmation(context,'Commerce TEST',const {'status':'pending','facebook_url':'https://www.facebook.com/qa-shop'},openFacebook:(_)async{calls++;}),child:const Text('Open'))))));
  await tester.tap(find.text('Open'));await tester.pumpAndSettle();
  expect(find.text('Scan enregistré · points en attente'),findsOneWidget);
  expect(find.textContaining('crédités'),findsNothing);
  await tester.tap(find.text('Rester dans TUNIBIZ'));await tester.pumpAndSettle();
  await tester.pump(const Duration(seconds:5));expect(calls,0);
 });
 testWidgets('A missing or invalid target never opens an external URL',(tester)async{
  var calls=0;
  await tester.pumpWidget(MaterialApp(home:Scaffold(body:ScanConfirmation(shop:'Commerce TEST',result:const {'status':'welcome','points':0,'facebook_url':'https://facebook.com.evil.test/page'},openFacebook:(_)async{calls++;}))));
  expect(find.text('Ouvrir Facebook'),findsNothing);expect(find.text('Carte retrouvée · bonus déjà reçu'),findsOneWidget);
  await tester.pump(const Duration(seconds:5));expect(calls,0);
 });
}
