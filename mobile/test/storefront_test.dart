import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tunibiz_mobile/api.dart';
import 'package:tunibiz_mobile/storefront.dart';
class StoreFake extends Api{
 bool claimed=false;
 final shop={'id':1,'name':'Café QA','category':'coffee','city':'Djerba','joined':true,'description':'Test'};
 @override Future<Map<String,dynamic>> call(String path,[Map<String,dynamic>? body])async{
 if(path=='/stores')return {'stores':[shop,{'id':2,'name':'Boutique QA','city':'Tunis','category':'clothing','joined':false}]};
 if(path=='/stores/1')return {...shop,'offers':[{'id':7,'kind':'pack','title':'Pack déjeuner','description':'Deux produits','starts':'2026-01-01','ends':'2026-12-31','old_price':20000,'new_price':15000},{'id':8,'kind':'coupon','title':'Coupon QA','description':'En caisse','discount':15,'starts':'2026-01-01','ends':'2026-12-31'}],'nearby':[],'coupons':claimed?[{'offer_id':8,'code':'TN-ABCDEF123456','used':null}]:[]};
 if(path=='/storefront/coupon/claim'){expect(body,{'id':8});claimed=true;return {'code':'TN-ABCDEF123456'};}
 throw StateError(path);
 }
}
void main(){
 testWidgets('Directory filter, storefront prices, coupon claim on compact phone',(t)async{
 t.view.physicalSize=const Size(320,640);t.view.devicePixelRatio=1;addTearDown(t.view.resetPhysicalSize);addTearDown(t.view.resetDevicePixelRatio);
 final api=StoreFake();addTearDown(api.close);
 await t.pumpWidget(MaterialApp(home:StoresPage(api:api)));await t.pumpAndSettle();
 expect(find.text('Café QA'),findsOneWidget);
 await t.tap(find.text('Mes commerces uniquement'));await t.pumpAndSettle();expect(find.text('Boutique QA'),findsNothing);
 await t.tap(find.text('Café QA'));await t.pumpAndSettle();
 await t.ensureVisible(find.text('Pack déjeuner'));expect(find.text('15.000 DT'),findsOneWidget);expect(find.text('20.000 DT'),findsOneWidget);
 await t.scrollUntilVisible(find.text('Obtenir mon coupon'),150);await t.ensureVisible(find.text('Obtenir mon coupon'));await t.pumpAndSettle();await t.tap(find.text('Obtenir mon coupon'));await t.pumpAndSettle();
 expect(api.claimed,isTrue);await t.ensureVisible(find.text('TN-ABCDEF123456'));expect(find.text('TN-ABCDEF123456'),findsOneWidget);
 expect(t.takeException(),isNull);
 });
}
