import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tunibiz_mobile/api.dart';
import 'package:tunibiz_mobile/mobile_repository.dart';
import 'package:tunibiz_mobile/mobile_support.dart';
import 'package:tunibiz_mobile/scan_history.dart';
class SupportApi extends Api {
 bool supported=true;final paths=<String>[];
 @override Future<Map<String,dynamic>> cached(String path)async{
  paths.add(path);
  if(path=='/mobile/capabilities'){if(!supported)throw const ApiUnavailable('Not found',cacheable:false);return {'version':1,'features':{'scan_history':true,'public_partners':true}};}
  if(path=='/mobile/partners')return {'stores':[{'id':6,'name':'Authorized TEST','slug':'authorized','city':'Djerba','category':'coffee','social':'https://www.facebook.com/test'}]};
  if(path=='/commerce/home')return {'profile':null,'stores':[],'offers':[],'sponsors':[]};
  if(path.startsWith('/mobile/business/scans'))return {'requests':[{'id':'approved','name':'TEST client','state':'approved','points':5,'created':1795200000}],'next_cursor':null};
  throw const ApiUnavailable('Not found',cacheable:false);
 }
}
void main(){
 test('only server-approved partners are merged and an older server is supported',()async{
  final api=SupportApi();addTearDown(api.close);
  final home=await MobileRepository(api).home();expect((home.home['stores'] as List).single['id'],6);expect((home.home['stores'] as List).single['partial'],true);
  expect((await MobileRepository(api).publicPartnerById(6))!['name'],'Authorized TEST');
  final old=SupportApi()..supported=false;addTearDown(old.close);
  expect((await MobileRepository(old).home()).home['stores'],isEmpty);expect(MobileSupport(old).has('scan_history'),false);
 });
 testWidgets('native merchant history renders server status and filters by state',(t)async{
  final api=SupportApi();addTearDown(api.close);
  await t.pumpWidget(MaterialApp(home:ScanHistoryPage(api:api)));await t.pumpAndSettle();
  expect(find.text('TEST client'),findsOneWidget);expect(find.text('+5 points'),findsOneWidget);
  await t.tap(find.text('Validé').first);await t.pumpAndSettle();expect(api.paths.last,contains('state=approved'));expect(t.takeException(),isNull);
  await t.pumpWidget(const SizedBox());await t.pumpAndSettle();
 });
}
