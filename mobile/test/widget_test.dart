import 'package:flutter_test/flutter_test.dart';
import 'package:tunibiz_mobile/main.dart';
void main(){
 test('amount is formatted in Tunisian dinars',(){expect(money(3500),'3.500 DT');});
 testWidgets('home exposes both journeys',(tester) async {
  await tester.pumpWidget(const Tunibiz());
  expect(find.text('Espace commerçant'),findsOneWidget);
  expect(find.text('Ma carte fidélité'),findsOneWidget);
 });
}
