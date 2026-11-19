import 'package:flutter/material.dart';
import 'package:tunibiz_mobile/reward_tile.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tunibiz_mobile/main.dart';
import 'package:tunibiz_mobile/premium.dart';
import 'package:tunibiz_mobile/api.dart';
import 'package:tunibiz_mobile/consumer_shell.dart';
class ShellApi extends Api {
 @override Future<bool> restore() async => false;
 @override Future<void> init() async {}
 @override Future<Map<String,dynamic>> call(String path,[Map<String,dynamic>? body]) async {
  if(path=='/stores')return {'stores':[]};
  throw StateError(path);
 }
}

void main(){
 test('amount is formatted in Tunisian dinars',(){expect(money(3500),'3.500 DT');});
 testWidgets('five consumer tabs preserve navigation and scanner requires account', (tester) async {
  tester.view.physicalSize=const Size(320,700);tester.view.devicePixelRatio=1;
  addTearDown(tester.view.resetPhysicalSize);addTearDown(tester.view.resetDevicePixelRatio);
  final api=ShellApi();addTearDown(api.close);
  await tester.pumpWidget(MaterialApp(home:ConsumerShell(apiOverride:api,cardBuilder:(_,__)=>const SizedBox(),businessBuilder:()=>const Scaffold(body:Text('Business QA')))));
  await tester.pumpAndSettle();
  expect(find.byType(NavigationDestination),findsNWidgets(5));
  expect(find.text('Le commerce local vous récompense.'),findsOneWidget);
  await tester.tap(find.widgetWithText(NavigationDestination,'Établissements'));await tester.pumpAndSettle();
  expect(find.text('Nos établissements'),findsOneWidget);
  await tester.tap(find.widgetWithText(NavigationDestination,'Scanner'));await tester.pumpAndSettle();
  expect(find.text('Connexion au portefeuille'),findsOneWidget);
  await tester.enterText(find.widgetWithText(TextField,'Email'),'saved@example.test');
  await tester.tap(find.widgetWithText(NavigationDestination,'Nearby'));await tester.pumpAndSettle();
  expect(find.text('TUNIBIZ Nearby'),findsOneWidget);
  await tester.tap(find.widgetWithText(NavigationDestination,'Portefeuille'));await tester.pumpAndSettle();
  expect(find.text('saved@example.test'),findsOneWidget);
  expect(tester.takeException(),isNull);
  await tester.pumpWidget(const SizedBox());await tester.pumpAndSettle();
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
