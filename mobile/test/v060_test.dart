import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tunibiz_mobile/api.dart';
import 'package:tunibiz_mobile/mobile_repository.dart';
import 'package:tunibiz_mobile/secure_cache.dart';
import 'package:tunibiz_mobile/external_links.dart';
import 'package:tunibiz_mobile/relationship.dart';
import 'package:tunibiz_mobile/app_language.dart';

class PartnerApi extends Api {
 bool pilotAvailable=true;
 @override Future<Map<String,dynamic>> cached(String path)async{
  if(path=='/commerce/home')return {'profile':{'name':'TEST'},'stores':[],'offers':[],'sponsors':[]};
  if(path=='/wallet')return {'cards':[{'shop_id':4,'id':14,'points':50},{'shop_id':5,'id':15,'points':7}]};
  if(path=='/commerce/profile')return {'notifications':[]};
  if(path.startsWith('/store/')&&pilotAvailable)return {'shop':{'id':4,'slug':pilotPartners.keys.first,'name':'المخزن الجربي','city':'Djerba'}};
  throw const ApiUnavailable('Network unavailable');
 }
}
void main(){
 TestWidgetsFlutterBinding.ensureInitialized();
 tearDown(()async{AppLanguage.locale.value=const Locale('fr');await SecureCache.clear('wallet');await SecureCache.clear('merchant');});
 test('approved public QR partner appears without inventing contact or combining balances',()async{
  final api=PartnerApi();addTearDown(api.close);
  final result=await MobileRepository(api).home();
  final stores=result.home['stores'] as List;
  expect(stores.single['name'],'المخزن الجربي');expect(stores.single['points'],50);
  expect(stores.single['address'],'');expect(stores.single['offers'],isEmpty);
  expect((result.wallet!['cards'] as List).last['points'],7);
  api.pilotAvailable=false;
  expect((await MobileRepository(api).home()).home['stores'],isEmpty);
 });
 test('private read cache is scoped, flagged and removed on logout',()async{
  await SecureCache.put('wallet','/wallet',{'points':50});
  expect((await SecureCache.read('wallet','/wallet'))!['_cached'],true);
  expect(await SecureCache.read('merchant','/wallet'),isNull);
  await SecureCache.clear('wallet');expect(await SecureCache.read('wallet','/wallet'),isNull);
 });
 test('social URL validation rejects executable and credential-bearing links',(){
  for(final value in ['javascript:alert(1)','http://facebook.com/a','https://u:p@facebook.com/a','https://facebook.com:444/a','https://facebook.com/a b']){
   expect(safeWebUrl(value),isNull,reason:value);
  }
  expect(socialLinks('https://facebook.com/pilot\nhttps://instagram.com/pilot')['facebook'],'https://facebook.com/pilot');
  expect(socialLinks('https://facebook.com.attacker.test/pilot'),isEmpty);
 });
 testWidgets('native role chooser switches to Arabic RTL and English',(tester)async{
  tester.view.physicalSize=const Size(390,844);tester.view.devicePixelRatio=1;
  addTearDown(tester.view.resetPhysicalSize);addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(const Tunibiz());await tester.pumpAndSettle();
  expect(find.text('Espace client'),findsOneWidget);
  await tester.tap(find.text('العربية'));await tester.pumpAndSettle();
  expect(Directionality.of(tester.element(find.byType(LanguagePicker))),TextDirection.rtl);
  await tester.tap(find.text('EN'));await tester.pumpAndSettle();
  expect(tr('Se connecter'),'Sign in');
  expect(tester.takeException(),isNull);
  await tester.pumpWidget(const SizedBox());await tester.pumpAndSettle();
 });
}
