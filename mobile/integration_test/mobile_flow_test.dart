// Acceptance against a separate database served by tool/qa_server.py.
// Never points test writes at production. Google/email transport/FCM are not mocked as success.
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:tunibiz_mobile/relationship.dart';
import 'package:tunibiz_mobile/api.dart';
import 'package:tunibiz_mobile/app_language.dart';
import 'package:tunibiz_mobile/commerce_business.dart';
import 'package:tunibiz_mobile/checkout_scanner.dart';
import 'package:tunibiz_mobile/store_scan.dart';
import 'package:tunibiz_mobile/loyalty_qr.dart';
import 'package:tunibiz_mobile/storefront.dart';
import 'package:tunibiz_mobile/nearby.dart';
import 'package:tunibiz_mobile/session_vault.dart';

void main(){
 final binding=IntegrationTestWidgetsFlutterBinding.ensureInitialized();
 const qa='http://10.0.2.2:8879';
 testWidgets('native commercial journeys against isolated real backend',(tester)async{
  final client=Api(scope:'wallet',serverUrl:qa);
  final merchant=Api(scope:'merchant',serverUrl:qa);
  final other=Api(serverUrl:qa);
  final screenshots=<String>[];
  Future<void> settle([int ms=1000])async{await tester.pump(Duration(milliseconds:ms));}
  Future<void> waitFor(Finder f,{int seconds=35})async{
   for(var i=0;i<seconds*4;i++){await tester.pump(const Duration(milliseconds:250));if(f.evaluate().isNotEmpty)return;}
   throw TestFailure('Not displayed: $f');
  }
  Future<void> tap(String text)async{
   final f=find.text(text).last;await waitFor(f);await tester.ensureVisible(f);await tester.pump(const Duration(milliseconds:200));await tester.tap(f);await settle();
  }
  Future<void> snap(String name)async{
   await tester.pump(const Duration(milliseconds:500));
   final shot=await binding.takeScreenshot(name);
   final file=File('/sdcard/Android/data/tn.tunibiz.tunibiz_mobile/files/screenshots/$name.png');
   await file.parent.create(recursive:true);await file.writeAsBytes(shot);
   binding.reportData?.remove('screenshots');screenshots.add(name);binding.reportData!['capture_names']=screenshots;
  }
  Future<void> screen(Widget page)async{
   await tester.pumpWidget(const SizedBox());await tester.pump();
   await tester.pumpWidget(MaterialApp(key:UniqueKey(),theme:tunibizTheme(),home:page));
   await settle(1800);
  }
  Future<void> field(String label,String value)async{
   final f=find.byWidgetPredicate((w)=>w is TextField&&w.decoration?.labelText==label);
   await waitFor(f);await tester.ensureVisible(f.last);await tester.enterText(f.last,value);await settle(200);
  }
  Future<void> nav(String label)async{await tester.tap(find.descendant(of:find.byType(NavigationBar),matching:find.text(label)).last);await settle();}
  try{
   await SessionVault.write('wallet',null);await SessionVault.write('merchant',null);
   await SessionVault.write('analytics','no');await SessionVault.write('push_consent','no');
   await tester.pumpWidget(Tunibiz(clientApiOverride:client,businessApiOverride:merchant));await settle();
   await binding.convertFlutterSurfaceToImage();await settle();
   await snap('01-accueil-fr');
   await tap('العربية');expect(Directionality.of(tester.element(find.byType(LanguagePicker))),TextDirection.rtl);await snap('02-accueil-ar-rtl');
   await tap('EN');await snap('03-accueil-en');await tap('FR');
   await tap('Espace client');await waitFor(find.text('Se connecter'));await snap('04-connexion-client');
   await tap('Créer un compte gratuit');
   final registered='android.qa.${DateTime.now().millisecondsSinceEpoch}@example.test';
   await field('Votre nom','Inscription Android TEST');await field('Email',registered);await field('Mot de passe','QA-Client-060!');
   await tap('Créer mon portefeuille');await waitFor(find.text('Mes points par établissement'));await snap('04b-compte-cree');
   expect((await client.call('/verification/status'))['verified'],false);
   final transport=HttpClient();final req=await transport.postUrl(Uri.parse('$qa/__qa__/verification'));
   req.headers.contentType=ContentType.json;req.headers.set('X-CSRF-Token',client.csrf);req.cookies.addAll(client.cookies.values);req.write(jsonEncode({'email':registered}));
   final response=await req.close();expect(response.statusCode,200);final fixture=jsonDecode(await utf8.decoder.bind(response).join()) as Map;transport.close();expect((fixture['token'] as String).length,43);
   await client.call('/verification/confirm',{'token':fixture['token']});
   expect((await client.call('/verification/status'))['verified'],true);
   await nav('Profil');await tap('Supprimer mon compte');await field('Confirmer le mot de passe','QA-Client-060!');
   await tap('Supprimer definitivement');await waitFor(find.text('Se connecter'));
   await field('Email','client.qa@example.test');await field('Mot de passe','QA-Client-060!');
   await tap('Se connecter');await waitFor(find.text('Mes points par établissement'));await snap('05-client-accueil');
   expect((await client.call('/wallet'))['cards'].map((c)=>c['points']).toSet(),{50,7});
   await nav('Mes cartes');await snap('06-cartes');
   // Open real selected membership using the same native production widget.
   final cards=(await client.call('/wallet'))['cards'] as List;
   final cid=cards.firstWhere((c)=>c['shop_id']==4)['id'];
   await client.call('/wallet/select',{'id':cid});final loyalty=await client.call('/loyalty');
   await screen(Workspace(merchant:false,sharedApi:client,initialData:loyalty));await snap('07-carte-fidelite');
   await tap('Présenter ma carte QR');await waitFor(find.byWidgetPredicate((w)=>w is CustomPaint&&w.painter is QrMatrixPainter));await settle();await snap('08-qr-client-temporaire');
   await screen(Home(apiOverride:client,businessApiOverride:merchant));await waitFor(find.text('Mes points par établissement'));
   await nav('Explorer');await snap('09-catalogue-partenaires');
   await screen(StorePage(api:client,id:4));await settle();await snap('10-pilote-vitrine-partielle');
   await screen(Home(apiOverride:client,businessApiOverride:merchant));await waitFor(find.text('Mes points par établissement'));
   await nav('Offres');await snap('11-offres-client');
   await nav('Profil');await snap('12-profil-client');
   await screen(Nearby(apiOverride:client));await settle();await snap('13-nearby-sans-gps');
   await screen(CommerceBusiness(apiOverride:merchant));await waitFor(find.text('Se connecter'));await snap('13b-connexion-business');
   await field('Adresse e-mail','merchant.qa@example.test');await field('Mot de passe','QA-Merchant-060!');
   await tap('Se connecter');await waitFor(find.byType(NavigationBar));

   final fixedQr=await merchant.call('/crm/store-qr');
   final qrFile=File('/sdcard/Android/data/tn.tunibiz.tunibiz_mobile/files/qa-partner.png');
   await qrFile.parent.create(recursive:true);await qrFile.writeAsBytes(base64Decode(fixedQr['png']));
   await screen(Home(apiOverride:client,businessApiOverride:merchant));await waitFor(find.text('Mes points par établissement'));
   await tester.tap(find.byType(FloatingActionButton));await waitFor(find.byType(CheckoutScanner));await settle(1200);await snap('14-camera-scanner');
   // The actual native ML Kit image decoder reads the unmodified existing merchant QR.
   await (tester.state(find.byType(CheckoutScanner)) as dynamic).analyzePath(qrFile.path);
   await waitFor(find.text('Scan enregistré · points en attente'));await snap('15-scan-en-attente');
   expect((await client.call('/wallet'))['cards'].firstWhere((c)=>c['shop_id']==4)['points'],50);
   await tap('Terminé');
   final pending=(await merchant.call('/crm/store-scans'))['requests'] as List;expect(pending,isNotEmpty);
   await other.init();await other.call('/login',{'email':'other.qa@example.test','password':'QA-Merchant-060!'});
   expect((await other.call('/crm/store-scans'))['requests'],isEmpty);
   await expectLater(other.call('/crm/store-scan/decide',{'id':pending.first['id'],'action':'approve','points':5}),throwsA(isA<ApiUnavailable>()));
   await screen(StoreApprovals(api:merchant));await waitFor(find.byTooltip('Valider'));await snap('16-validations-qr');
   await tester.ensureVisible(find.byTooltip('Valider').last);await tester.tap(find.byTooltip('Valider').last);await settle();
   await tester.enterText(find.byType(TextFormField).last,'5');await tap('Confirmer');
   await waitFor(find.text('Validé : +5 points'));await snap('17-scan-valide');
   final duplicate=await merchant.call('/crm/store-scan/decide',{'id':pending.first['id'],'action':'approve','points':5});expect(duplicate['duplicate'],true);
   expect((await client.call('/wallet'))['cards'].firstWhere((c)=>c['shop_id']==4)['points'],55);
   await screen(CommerceBusiness(apiOverride:merchant));await waitFor(find.byType(NavigationBar));await snap('18-business-dashboard');
   await nav('Clients');await field('Téléphone du client','20123456');await tap('Rechercher');await snap('19-clients-recherche');
   await tap('Ajouter des points');await snap('20-attribution-points');await field('Motif','Recette Android +20 TEST');await tap('Valider');
   await settle(1500);expect((await client.call('/wallet'))['cards'].firstWhere((c)=>c['shop_id']==4)['points'],75);
   expect((await client.call('/wallet'))['cards'].firstWhere((c)=>c['shop_id']==5)['points'],7);
   await nav('Promotions');await snap('21-promotions-business');
   await tap('Créer une promotion');await snap('22-formulaire-promotion');
   await field('Titre','Promotion Android TEST');await field('Description','Conditions de recette Android');
   await field('Réduction (%) si applicable','20');await field('Conditions','Données TEST isolées');
   await tap('Valider');await waitFor(find.text('APERÇU CLIENT'));await snap('22b-apercu-promotion');await tap('Enregistrer');
   await settle(1800);
   final offers=(await merchant.call('/commerce/business'))['promotions'] as List;
   final promo=offers.firstWhere((o)=>o['title']=='Promotion Android TEST');
   expect(promo['id'],isNotNull);
   await nav('Vitrine');await snap('23-vitrine-business');
   await tap('Modifier la présentation');await snap('24-formulaire-vitrine');
   await field('Description','Vitrine modifiée par recette Android TEST');await tap('Valider');await settle(1800);
   await tap('Publier la vitrine');await settle(1800);
   expect((await client.call('/stores/4'))['description'],'Vitrine modifiée par recette Android TEST');
   await screen(StorePage(api:client,id:4));await waitFor(find.text('Vitrine modifiée par recette Android TEST'));await snap('25-vitrine-publiee');
   await screen(Home(apiOverride:client,businessApiOverride:merchant));await waitFor(find.text('Mes points par établissement'));await snap('26-solde-client-actualise');
   await nav('Offres');await snap('27-promotion-visible-client');
   expect((await client.call('/commerce/home'))['offers'].any((o)=>o['id']==promo['id']),true);
   expect((await client.call('/commerce/profile'))['notifications'],isNotEmpty);
   expect(await SessionVault.read('wallet'),isNotEmpty);expect(await SessionVault.read('merchant'),isNotEmpty);
   await client.call('/wallet/logout',{});expect(await SessionVault.read('wallet'),isNull);
   await client.init();await client.call('/wallet/login',{'email':'client.qa@example.test','password':'QA-Client-060!'});
   expect((await client.call('/wallet'))['cards'].firstWhere((c)=>c['shop_id']==4)['points'],75);
   await screen(Home(apiOverride:client,businessApiOverride:merchant));await waitFor(find.text('Mes points par établissement'));
   await merchant.call('/commerce/points',{'id':cid,'points':1,'reason':'Actualisation automatique TEST','key':'auto-refresh-${DateTime.now().microsecondsSinceEpoch}'});
   await waitFor(find.text('76 points'),seconds:45);await snap('27b-actualisation-automatique');
   expect(await const MethodChannel('tn.tunibiz/private').invokeMethod<bool>('loyaltyNotice',{'id':'qa-validated-points','body':'Points TEST confirmés par le serveur.'}),true);
   await client.cached('/commerce/home');await client.cached('/wallet');await client.cached('/commerce/profile');
   await snap('28-offline-prepare');
   const stagePath='/sdcard/Android/data/tn.tunibiz.tunibiz_mobile/files/qa-network';
   Future<void> networkStage(String phase)async{
    await File(stagePath).writeAsString(phase);
    for(var i=0;i<60;i++){try{if(await File('$stagePath-ack').readAsString()==phase)return;}catch(_){}await Future<void>.delayed(const Duration(milliseconds:250));}
    throw TestFailure('ADB network stage did not complete: $phase');
   }
   await networkStage('offline');
   final offline=Api(scope:'wallet',serverUrl:qa,requestTimeout:const Duration(seconds:3));
   offline.signedIn=true;offline.restored=true;offline.cookies.addAll(client.cookies);
   try{
    await screen(Home(apiOverride:offline,businessApiOverride:merchant));
    await waitFor(find.text('Hors connexion · dernières données enregistrées'),seconds:25);
    await snap('29-client-hors-connexion');
    await tester.tap(find.byType(FloatingActionButton));await settle();
    expect(find.text('Connectez-vous pour enregistrer une opération.'),findsOneWidget);
    await nav('Profil');await tap('Déconnexion');await waitFor(find.text('Se connecter'));
    expect(await SessionVault.read('wallet'),isNull);await snap('30-deconnexion-client-hors-connexion');
    await screen(CommerceBusiness(apiOverride:merchant));await waitFor(find.text('Hors connexion · dernières données enregistrées'),seconds:40);
    await snap('31-business-hors-connexion');await nav('Plus');await tap('Paramètres');await tap('Déconnexion');
    await waitFor(find.text('Se connecter'));expect(await SessionVault.read('merchant'),isNull);await snap('32-deconnexion-business-hors-connexion');

   }finally{await networkStage('online');offline.close();}
   binding.reportData??={};binding.reportData!.addAll({'capture_names':screenshots,'qr_decode':'native ML Kit image','isolated_backend':true,'real_google_login':false,'real_fcm_delivery':false,'native_notification':true,'automatic_balance_refresh':true,'offline_logout_both_roles':true});
  }finally{
   await tester.pumpWidget(const SizedBox());await settle(100);
   client.close();merchant.close();other.close();
  }
 });
}
