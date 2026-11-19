import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tunibiz_mobile/business_dashboard.dart';
void main(){
 testWidgets('business dashboard uses recorded data and changes time period',(tester)async{
  tester.view.physicalSize=const Size(320,844);tester.view.devicePixelRatio=1;
  addTearDown(tester.view.resetPhysicalSize);addTearDown(tester.view.resetDevicePixelRatio);
  final d=<String,dynamic>{'stats':{'customers':5,'points':180,'spent':120000,'consented':3},'dashboard':{'shop':{'name':'QA Shop'},'buyers':4,'repeat_buyers':2,'active_campaigns':1,'active_nearby':2,'daily':List.generate(30,(i)=>{'day':'2026-10-'+(i+1).toString().padLeft(2,'0'),'amount':i==0?80000:i==29?40000:0,'purchases':i==0?2:i==29?1:0,'amount_purchases':(i==0||i==29)?1:0})}};
  (d['dashboard'] as Map)['subscription']={'status':'active','paid_until':'2026-12-20'};
  (d['dashboard'] as Map)['pilot']={'new_customers':2,'active_customers':3,'pending_qr':1,'points_issued':200,'coupons_claimed':5,'coupons_used':2};
  await tester.pumpWidget(MaterialApp(home:Scaffold(body:SingleChildScrollView(child:BusinessDashboard(data:d)))));
  expect(find.text('Abonnement active · 19 DT / mois'),findsOneWidget);
  expect(find.text('QA Shop'),findsOneWidget);expect(find.text('40.000 DT'),findsOneWidget);
  await tester.ensureVisible(find.text('30 jours'));await tester.tap(find.text('30 jours'));await tester.pumpAndSettle();
  expect(find.text('120.000 DT'),findsNWidgets(2));
  expect(find.text('3 achat(s) · 60.000 DT panier moyen renseigné'),findsOneWidget);expect(tester.takeException(),isNull);
 });
}
