import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tunibiz_mobile/api.dart';
import 'package:tunibiz_mobile/relationship.dart';
import 'package:tunibiz_mobile/commerce_client.dart';
import 'package:tunibiz_mobile/app_language.dart';
class CatalogueApi extends Api {
 CatalogueApi(){signedIn=true;restored=true;csrf='test';}
 @override Future<void> init() async {}
 @override Future<Map<String,dynamic>> cached(String path)async{
  if(path=='/commerce/home')return {'profile':{'id':1,'name':'TEST'},'stores':[{'id':4,'name':'المخزن الجربي — TEST','city':'Djerba','category':'grocery','offers_count':1}],'offers':[],'sponsors':[]};
  if(path=='/wallet')return {'cards':[]};
  if(path=='/commerce/profile')return {'notifications':[]};
  throw StateError(path);
 }
}
void main(){
 testWidgets('Arabic partner card remains within a narrow catalogue at enlarged text size',(tester)async{
  tester.view.physicalSize=const Size(390,844);tester.view.devicePixelRatio=1;
  addTearDown(tester.view.resetPhysicalSize);addTearDown(tester.view.resetDevicePixelRatio);
  final api=CatalogueApi();addTearDown(api.close);
  await tester.pumpWidget(MaterialApp(theme:tunibizTheme(),builder:(_,child)=>MediaQuery(data:const MediaQueryData(textScaler:TextScaler.linear(1.3)),child:child!),home:CommerceClient(apiOverride:api,cardBuilder:(_,__)=>const SizedBox(),businessBuilder:()=>const SizedBox())));
  await tester.pumpAndSettle();
  await tester.tap(find.descendant(of:find.byType(NavigationBar),matching:find.text('Explorer')));await tester.pumpAndSettle();
  await tester.ensureVisible(find.text('المخزن الجربي — TEST'));await tester.pumpAndSettle();
  expect(tester.takeException(),isNull);
  await tester.pumpWidget(const SizedBox());await tester.pumpAndSettle();
  AppLanguage.locale.value=const Locale('fr');
 });
}
