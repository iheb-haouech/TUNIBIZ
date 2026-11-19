import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tunibiz_mobile/api.dart';
import 'package:tunibiz_mobile/wallet.dart';

class WalletFakeApi extends Api{
 final calls=<String>[];
 final cards=<Map<String,dynamic>>[
 {'id':1,'shop':'Cafe QA','city':'Tunisie','points':135,'eligible':1},
 {'id':2,'shop':'Shop QA','city':'Tunisie','points':80,'eligible':0}
 ];
 int? selected;
 @override Future<void> init()async{}
 @override Future<Map<String,dynamic>> call(String path,[Map<String,dynamic>? body])async{
  calls.add(path);
  switch(path){
   case '/wallet/login':return {'ok':true};
   case '/wallet':return {'profile':{'name':'QA Client','email':'qa@example.test'},'cards':cards};
   case '/wallet/select':selected=body!['id'] as int;return {'ok':true};
   case '/loyalty':return {'shop':cards.firstWhere((c)=>c['id']==selected)['shop']};
   case '/wallet/unlink':cards.removeWhere((c)=>c['id']==body!['id']);return {'ok':true};
   case '/wallet/logout':return {'ok':true};
   default:throw StateError(path);
  }
 }
}
void main(){
 testWidgets('Wallet cards open corresponding shop and removal requires confirmation',(tester)async{
  tester.view.physicalSize=const Size(390,844);tester.view.devicePixelRatio=1;
  addTearDown(tester.view.resetPhysicalSize);addTearDown(tester.view.resetDevicePixelRatio);
  final api=WalletFakeApi();addTearDown(api.close);
  await tester.pumpWidget(MaterialApp(home:ConsumerWallet(apiOverride:api,cardBuilder:(api,d)=>Scaffold(appBar:AppBar(),body:Text(d['shop'])))));
  await tester.pumpAndSettle();
  await tester.enterText(find.byType(TextField).at(0),'qa@example.test');
  await tester.enterText(find.byType(TextField).at(1),'Long-Test-Passphrase');
  await tester.ensureVisible(find.text('Se connecter'));await tester.tap(find.text('Se connecter'));await tester.pumpAndSettle();
  expect(find.text('135 pts'),findsOneWidget);expect(find.byType(WalletCard),findsWidgets);
  final card=find.widgetWithText(WalletCard,'Cafe QA');
  await tester.ensureVisible(card);await tester.tap(find.descendant(of:card,matching:find.text('Ouvrir')));await tester.pumpAndSettle();
  expect(api.selected,1);expect(find.text('Cafe QA'),findsOneWidget);
  await tester.pageBack();await tester.pumpAndSettle();
  final remove=find.descendant(of:find.widgetWithText(WalletCard,'Cafe QA'),matching:find.byTooltip('Retirer la carte'));
  await tester.ensureVisible(remove);await tester.tap(remove);await tester.pumpAndSettle();
  expect(find.text('Retirer cette carte ?'),findsOneWidget);
  await tester.tap(find.widgetWithText(FilledButton,'Retirer'));await tester.pumpAndSettle();
  expect(api.cards.length,1);expect(api.calls.contains('/wallet/unlink'),isTrue);
  expect(tester.takeException(),isNull);
 });
}
