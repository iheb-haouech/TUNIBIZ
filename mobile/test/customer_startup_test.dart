import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tunibiz_mobile/api.dart';
import 'package:tunibiz_mobile/wallet.dart';
class ResumeApi extends Api{
 final requests=<String>[];int scans=0;
 @override Future<bool> restore()async{signedIn=true;return true;}
 @override Future<void> init()async{}
 @override Future<Map<String,dynamic>> call(String path,[Map<String,dynamic>? body])async{
 requests.add(path);
 if(path=='/wallet')return {'profile':{'name':'QA Client','email':'qa@example.test'},'cards':[]};
 if(path=='/store/shop-qa')return {'shop':{'name':'Commerce QA'}};
 if(path=='/wallet/store-scan'){expect(body,{'slug':'shop-qa'});scans++;return scans==1?{'status':'welcome','points':3}:{'status':'pending','id':'qa-request'};}
 if(path=='/wallet/store-scans')return {'requests':[]};
 throw StateError(path);
 }
}
void main(){
 testWidgets('restored account can scan directly and sees welcome then pending validation',(tester)async{
 tester.view.physicalSize=const Size(390,844);tester.view.devicePixelRatio=1;
 addTearDown(tester.view.resetPhysicalSize);addTearDown(tester.view.resetDevicePixelRatio);
 final api=ResumeApi();addTearDown(api.close);
 await tester.pumpWidget(MaterialApp(home:ConsumerWallet(apiOverride:api,scanOnOpen:true,scannerOverride:(_)async=>'shop-qa',cardBuilder:(_,__)=>const SizedBox())));
 await tester.pumpAndSettle();
 expect(find.text('+3 points de bienvenue crédités'),findsOneWidget);
 expect(api.scans,1);expect(api.requests.contains('/wallet/login'),isFalse);
 await tester.tap(find.text('Terminé'));await tester.pumpAndSettle();
 await tester.ensureVisible(find.text('Scanner le QR du commerce'));await tester.tap(find.text('Scanner le QR du commerce'));await tester.pumpAndSettle();
 expect(find.text('Scan enregistré · points en attente'),findsOneWidget);expect(api.scans,2);
 await tester.tap(find.text('Terminé'));await tester.pumpAndSettle();
 expect(find.text('Bonjour QA Client'),findsOneWidget);expect(tester.takeException(),isNull);
 await tester.pumpWidget(const SizedBox());await tester.pumpAndSettle();
 });
}
