import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tunibiz_mobile/account_actions.dart';
import 'package:tunibiz_mobile/password_recovery.dart';
import 'package:tunibiz_mobile/api.dart';
class AccountApi extends Api {
 bool verified=false,confirmOwn=true,resetDenied=false;final posts=<String,Map<String,dynamic>>{};
 AccountApi(){csrf='qa';signedIn=true;}
 @override Future<void> init()async{csrf='qa';}
 @override Future<Map<String,dynamic>> call(String path,[Map<String,dynamic>? body])async{
  if(body!=null)posts[path]=body;
  if(path=='/verification/status')return {'verified':verified,'delivery_enabled':true};
  if(path=='/verification/confirm'){verified=confirmOwn;return {'message':'done'};}
  if(path=='/password/request')return {'message':'Si un compte correspondant existe, un lien sera envoyé.'};
  if(path=='/password/reset'){if(resetDenied)throw const ApiUnavailable('Lien expiré ou déjà utilisé',cacheable:false);return {'message':'done'};}
  throw StateError(path);
 }
}
Future<void> field(WidgetTester t,String label,String value)async{
 final f=find.byWidgetPredicate((w)=>w is TextField&&w.decoration?.labelText==label);
 if(f.evaluate().isEmpty)await t.scrollUntilVisible(f,220,scrollable:find.byType(Scrollable).first);
 await t.ensureVisible(f.last);await t.enterText(f.last,value);await t.pumpAndSettle();
}
Future<void> tap(WidgetTester t,String label)async{
 final f=find.text(label);if(f.evaluate().isEmpty)await t.scrollUntilVisible(f,220,scrollable:find.byType(Scrollable).first);
 await t.ensureVisible(f.last);await t.tap(f.last);await t.pumpAndSettle();
}
void main(){
 final token=List.filled(43,'a').join();
 test('account links reject foreign origins, ambiguous tokens and executable inputs',(){
  expect(accountActionToken(token,'/verify-email'),token);
  expect(accountActionToken('https://ihebhaouech.pythonanywhere.com/verify-email?token=$token','/verify-email'),token);
  for(final value in ['http://ihebhaouech.pythonanywhere.com/verify-email?token=$token','https://attacker.test/verify-email?token=$token','https://ihebhaouech.pythonanywhere.com:443/verify-email?token=$token','https://u:p@ihebhaouech.pythonanywhere.com/verify-email?token=$token','https://ihebhaouech.pythonanywhere.com/verify-email?token=$token&token=$token','https://ihebhaouech.pythonanywhere.com/verify-email?token=$token#x','https://ihebhaouech.pythonanywhere.com/reset-password?token=$token','javascript:alert(1)']){
   expect(accountActionToken(value,'/verify-email'),isNull,reason:value);
  }
 });
 testWidgets('native recovery requests the selected account type and waits for reset success',(t)async{
  final api=AccountApi();addTearDown(api.close);
  await t.pumpWidget(MaterialApp(home:PasswordRecoveryPage(kind:'merchant',initialEmail:'qa@example.test',apiOverride:api)));await t.pumpAndSettle();
  await tap(t,'Recevoir un lien de réinitialisation');expect(api.posts['/password/request']!['kind'],'merchant');
  await field(t,'Lien de réinitialisation','https://ihebhaouech.pythonanywhere.com/reset-password?token=$token');
  await field(t,'Nouveau mot de passe','QA-password-061!');await field(t,'Répéter le mot de passe','different-password');
  await tap(t,'Enregistrer le nouveau mot de passe');expect(api.posts.containsKey('/password/reset'),false);
  await field(t,'Répéter le mot de passe','QA-password-061!');api.resetDenied=true;
  await tap(t,'Enregistrer le nouveau mot de passe');expect(find.text('Mot de passe modifié'),findsNothing);
  expect(find.text('Lien expiré ou déjà utilisé'),findsOneWidget);
  api.resetDenied=false;await tap(t,'Enregistrer le nouveau mot de passe');expect(find.text('Mot de passe modifié'),findsOneWidget);
  expect(api.posts['/password/reset']!['token'],token);expect(t.takeException(),isNull);
  await t.pumpWidget(const SizedBox());await t.pumpAndSettle();
 });
 testWidgets('a confirmation link cannot mark the wrong signed-in account as verified',(t)async{
  final api=AccountApi()..confirmOwn=false;addTearDown(api.close);
  await t.pumpWidget(MaterialApp(home:EmailVerificationPage(api:api)));await t.pumpAndSettle();
  await field(t,'Lien de confirmation',token);await tap(t,'Confirmer mon adresse');
  expect(find.text('Adresse e-mail confirmée'),findsNothing);expect(find.text('Le lien a été traité. Vérifiez le compte connecté.'),findsOneWidget);
  api.confirmOwn=true;await field(t,'Lien de confirmation',token);await tap(t,'Confirmer mon adresse');
  expect(find.text('Adresse e-mail confirmée'),findsOneWidget);expect(t.takeException(),isNull);
  await t.pumpWidget(const SizedBox());await t.pumpAndSettle();
 });
}
