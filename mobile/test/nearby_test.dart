import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:tunibiz_mobile/api.dart';
import 'package:tunibiz_mobile/nearby.dart';

final testOffers=<Map<String,dynamic>>[
 {'id':1,'title':'QA Coffee','shop':'QA','category':'coffee','lat':33.88,'lon':10.86,'description':'Test conditions','address':'Test fixture','ends':'2026-12-01'},
 {'id':2,'title':'QA Food','shop':'QA','category':'restaurant','lat':33.881,'lon':10.861,'description':'Test conditions','address':'Test fixture','ends':'2026-12-01'},
 {'id':3,'title':'QA Far','shop':'QA','category':'shopping','lat':33.91,'lon':10.91},
];
class FakeApi extends Api{
 final calls=<String>[];
 @override Future<Map<String,dynamic>> call(String path,[Map<String,dynamic>? body])async{
  calls.add(path);expect(path,'/nearby');expect(body,isNull);return {'offers':testOffers};
 }
}
void main(){
 test('distance sorted nearest, 1km boundary, malformed coordinates excluded',(){
  final result=nearbyMatches([...testOffers,{'lat':double.nan,'lon':10.86}],const LatLng(33.88,10.865));
  expect(result.map((x)=>x['id']),[2,1]);
  expect(distanceMeters(0,0,0,0),0);expect(distanceMeters(0,0,0,.01),greaterThan(1000));
 });
 test('admin-configured per-offer radius changes eligibility',(){
 final items=[{...testOffers.first,'id':11,'radius':100},{...testOffers.first,'id':12,'radius':2000}];
 final found=nearbyMatches(items,const LatLng(33.88,10.865));
 expect(found.map((o)=>o['id']),[12]);
 });
 testWidgets('Nearby defaults to private radar, filters and clears location',(tester)async{
  tester.view.physicalSize=const Size(390,844);tester.view.devicePixelRatio=1;
  addTearDown(tester.view.resetPhysicalSize);addTearDown(tester.view.resetDevicePixelRatio);
  const channel=MethodChannel('tn.tunibiz/nearby');
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(channel,(call)async{
   if(call.method=='position')return {'lat':33.88,'lon':10.865,'accuracy':50.0};
   return false;
  });
  final api=FakeApi();
  addTearDown((){api.close();TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(channel,null);});
  await tester.pumpWidget(MaterialApp(home:Nearby(apiOverride:api)));
  expect(find.byType(FlutterMap),findsNothing);
  await tester.tap(find.text('Activer la découverte'));await tester.pumpAndSettle();
  expect(find.byType(FlutterMap),findsOneWidget);
  expect(find.byType(TileLayer),findsNothing);
  expect(tester.widget<MarkerLayer>(find.byType(MarkerLayer)).markers.length,3);
  await tester.tap(find.widgetWithText(FilterChip,'Cafés'));await tester.pumpAndSettle();
  expect(tester.widget<MarkerLayer>(find.byType(MarkerLayer)).markers.length,2);
  await tester.tap(find.text('Désactiver la découverte'));await tester.pumpAndSettle();
  expect(find.byType(FlutterMap),findsNothing);
  expect(api.calls,['/nearby']);
  await tester.pumpWidget(const SizedBox());await tester.pumpAndSettle();
  expect(tester.takeException(),isNull);
 });
}
