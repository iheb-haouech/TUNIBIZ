import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tunibiz_mobile/api.dart';
import 'package:tunibiz_mobile/commerce_client.dart';
import 'package:tunibiz_mobile/commerce_business.dart';

class CommerceApi extends Api{
 final bool authenticated;final calls=<String>[];Map<String,dynamic>? points;
 CommerceApi(this.authenticated){signedIn=authenticated;}
 @override Future<void> init()async{}
 @override Future<bool> restore()async=>authenticated;
 @override Future<Map<String,dynamic>> call(String path,[Map<String,dynamic>? body])async{
 calls.add(path);
 if(path=='/commerce/home')return {'profile':authenticated?{'name':'Client de recette','email':'qa@example.test'}:null,'stores':[],'offers':[],'sponsors':[],'categories':[],'preferences':{'marketing':0,'personalization':0}};
 if(path=='/wallet')return {'profile':{'name':'Client de recette','email':'qa@example.test'},'cards':[]};
 if(path=='/commerce/profile')return {'phone':null,'notifications':[]};
 if(path=='/verification/status')return {'verified':true,'required':false};
 if(path.startsWith('/commerce/business'))return {'profile':{'name':'Commerce de recette','city':'Djerba','photo':null,'published':0,'completeness':50},'stats':{'customers':1,'points_issued':20,'active_customers':1,'active_promotions':0,'new_customers':1,'repeat_customers':0,'advantages':0,'coupons_used':0},'daily':[],'customers':[{'id':1,'name':'Client de recette','phone':'+21620123456','points':20}],'promotions':[],'rewards':[],'activities':[]};
 if(path=='/commerce/points'){points=body;return {'ok':true};}
 throw StateError(path);
 }
}
void sizing(WidgetTester tester){tester.view.physicalSize=const Size(390,844);tester.view.devicePixelRatio=1;addTearDown(tester.view.resetPhysicalSize);addTearDown(tester.view.resetDevicePixelRatio);}
void main(){
 testWidgets('first opening requires account and shows graphical Google button',(tester)async{
 sizing(tester);final api=CommerceApi(false);addTearDown(api.close);
 await tester.pumpWidget(MaterialApp(home:CommerceClient(apiOverride:api,cardBuilder:(_,__)=>const SizedBox(),businessBuilder:()=>const SizedBox())));await tester.pumpAndSettle();
 expect(find.text('Se connecter'),findsOneWidget);expect(find.text('Continuer avec Google'),findsOneWidget);expect(find.byType(NavigationDestination),findsNothing);expect(find.text('Le commerce local vous récompense.'),findsNothing);expect(tester.takeException(),isNull);
 await tester.pumpWidget(const SizedBox());await tester.pumpAndSettle();
 });
 testWidgets('authenticated client has five tabs and a useful empty wallet',(tester)async{
 sizing(tester);final api=CommerceApi(true);addTearDown(api.close);
 await tester.pumpWidget(MaterialApp(home:CommerceClient(apiOverride:api,cardBuilder:(_,__)=>const SizedBox(),businessBuilder:()=>const SizedBox())));await tester.pumpAndSettle();
 expect(find.byType(NavigationDestination),findsNWidgets(5));expect(find.text('Bonjour Client de recette'),findsOneWidget);
 await tester.tap(find.widgetWithText(NavigationDestination,'Mes cartes'));await tester.pumpAndSettle();expect(find.text('Votre prochaine carte vous attend'),findsOneWidget);expect(find.text('Supprimer mon compte'),findsNothing);expect(tester.takeException(),isNull);
 await tester.pumpWidget(const SizedBox());await tester.pumpAndSettle();
 });
 testWidgets('business grants points without transaction price and keeps navigation',(tester)async{
 sizing(tester);final api=CommerceApi(true);addTearDown(api.close);
 await tester.pumpWidget(MaterialApp(home:CommerceBusiness(apiOverride:api)));await tester.pumpAndSettle();expect(tester.takeException(),isNull);
 await tester.tap(find.widgetWithText(NavigationDestination,'Clients'));await tester.pumpAndSettle();await tester.ensureVisible(find.text('Ajouter des points'));await tester.tap(find.text('Ajouter des points'));await tester.pumpAndSettle();
 await tester.enterText(find.widgetWithText(TextFormField,'Motif'),'Points de recette');await tester.tap(find.text('Valider'));await tester.pumpAndSettle();
 expect(api.points?['points'],20);expect(api.points?['reason'],'Points de recette');expect(api.points?.containsKey('amount'),false);expect(find.byType(NavigationDestination),findsNWidgets(5));expect(tester.takeException(),isNull);
 await tester.pumpWidget(const SizedBox());await tester.pumpAndSettle();
 });
}
