import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:tunibiz_mobile/business_offer.dart';
import 'package:tunibiz_mobile/business_nearby.dart';
import 'package:tunibiz_mobile/api.dart';

class FakeMerchant extends Api{
 @override Future<Map<String,dynamic>> call(String path,[Map<String,dynamic>? body])async{
 expect(path,'/nearby/business');return {'radius':500,'location':{'lat':33.88,'lon':10.86,'address':'Adresse QA'},'offers':[{'id':42,'title':'Promo QA','category':'restaurant','description':'Conditions QA','starts':'2020-01-01','ends':'2099-12-31','active':1,'radius_override':750}]};
 }
}
void main(){
 test('artwork uses allowlisted categories and campaign status',(){
 expect(offerPhoto({'visual':'coffee'}),'assets/espresso.webp');
 expect(offerPhoto({'category':'restaurant'}),'assets/restaurant.webp');
 expect(offerPhoto({'visual':'https://example.com/a.png'}),isNull);
 expect(campaignStatus({'active':0}),'Arrêtée');
 expect(campaignStatus({'starts':'2099-01-01'}),'Programmée');
 expect(campaignStatus({'ends':'2020-01-01'}),'Terminée');
 });
 testWidgets('merchant Nearby displays real map, radius, artwork and stop action',(tester)async{
 tester.view.physicalSize=const Size(320,640);tester.view.devicePixelRatio=1;
 addTearDown(tester.view.resetPhysicalSize);addTearDown(tester.view.resetDevicePixelRatio);
 final api=FakeMerchant();addTearDown(api.close);int? stopped;
 await tester.pumpWidget(MaterialApp(home:Scaffold(body:SingleChildScrollView(child:BusinessNearby(api:api,onCreate:()async{},onLocation:()async{},onStop:(id)async{stopped=id;})))));
 await tester.pumpAndSettle();
 expect(find.byType(FlutterMap),findsOneWidget);
 expect(find.byType(TileLayer),findsNothing);
 expect(find.text('500 m'),findsOneWidget);
 expect(find.text('Rayon : 750 m'),findsOneWidget);
 expect(find.text('Promo QA'),findsOneWidget);
 expect(find.byType(Image),findsOneWidget);
 await tester.ensureVisible(find.text('Arrêter'));await tester.tap(find.text('Arrêter'));await tester.pumpAndSettle();
 expect(stopped,42);expect(tester.takeException(),isNull);
 });
 testWidgets('photo library returns chosen visual on a compact display',(tester)async{
 tester.view.physicalSize=const Size(320,640);tester.view.devicePixelRatio=1;
 addTearDown(tester.view.resetPhysicalSize);addTearDown(tester.view.resetDevicePixelRatio);
 String? selected;
 await tester.pumpWidget(MaterialApp(home:Scaffold(body:Builder(builder:(context)=>TextButton(onPressed:()async{selected=await chooseOfferVisual(context);},child:const Text('Choisir'))))));
 await tester.tap(find.text('Choisir'));await tester.pumpAndSettle();
 await tester.ensureVisible(find.text('Restaurant'));await tester.tap(find.text('Restaurant'));await tester.pumpAndSettle();
 expect(selected,'restaurant');expect(tester.takeException(),isNull);
 });
}
