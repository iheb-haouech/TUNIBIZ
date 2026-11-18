import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tunibiz_mobile/main.dart';
import 'package:tunibiz_mobile/premium.dart';
import 'package:tunibiz_mobile/reward_tile.dart';
void main(){
 test('amount is formatted in Tunisian dinars',(){expect(money(3500),'3.500 DT');});
 testWidgets('premium home opens loyalty, Nearby and merchant journeys',(tester) async {
  tester.view.physicalSize=const Size(390,844); tester.view.devicePixelRatio=1;
  addTearDown(tester.view.resetPhysicalSize);addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(const Tunibiz());await tester.pumpAndSettle();
  expect(find.text('Ma carte fidélité'),findsOneWidget);
  expect(find.byType(PremiumRing),findsOneWidget);
  expect(find.text('—'),findsOneWidget);
  await tester.tap(find.text('Ma carte fidélité'));await tester.pumpAndSettle();
  expect(find.text('Connectez votre carte'),findsOneWidget);
  await tester.pageBack();await tester.pumpAndSettle();
  await tester.tap(find.widgetWithText(NavigationDestination,'Business'));await tester.pumpAndSettle();
  expect(find.text('Connexion commerçant'),findsOneWidget);
  await tester.pageBack();await tester.pumpAndSettle();
  await tester.tap(find.widgetWithText(NavigationDestination,'Nearby'));await tester.pumpAndSettle();
  expect(find.text('TUNIBIZ Nearby'),findsOneWidget);
  expect(tester.takeException(),isNull);
 });
 testWidgets('premium ring uses real points and remains within small layout',(tester) async{
  tester.view.physicalSize=const Size(320,640);tester.view.devicePixelRatio=1;
  addTearDown(tester.view.resetPhysicalSize);addTearDown(tester.view.resetDevicePixelRatio);
  var clicked=false;
  await tester.pumpWidget(MaterialApp(home:Scaffold(body:SingleChildScrollView(child:PremiumHero(name:'Bonjour test',shop:'Commerce',description:'Votre prochaine récompense',action:'Récompenses',points:135,goal:200,signedIn:true,onAction:()=>clicked=true)))));
  expect(find.text('135'),findsOneWidget);expect(find.text('Objectif 200'),findsOneWidget);
  await tester.tap(find.text('Récompenses'));expect(clicked,isTrue);
  expect(tester.takeException(),isNull);
 });
 testWidgets('reward progress and eligibility use real balances',(tester)async{
  tester.view.physicalSize=const Size(320,640);tester.view.devicePixelRatio=1;
  addTearDown(tester.view.resetPhysicalSize);addTearDown(tester.view.resetDevicePixelRatio);
  final r={'title':'Café offert','cost':200,'visual':'coffee','description':'Sur place uniquement'};
  await tester.pumpWidget(MaterialApp(home:Scaffold(body:RewardTile(reward:r,points:135))));await tester.pumpAndSettle();
  expect(find.text('Encore 65 points'),findsOneWidget);expect(find.text('68 %'),findsOneWidget);
  expect(find.text('Photo illustrative'),findsOneWidget);expect(find.text('Sur place uniquement'),findsOneWidget);
  await tester.pumpWidget(MaterialApp(home:Scaffold(body:RewardTile(reward:r,points:200))));await tester.pumpAndSettle();
  expect(find.text('DISPONIBLE'),findsOneWidget);expect(find.text('100 %'),findsOneWidget);expect(tester.takeException(),isNull);
 });
}
