from pathlib import Path
p=Path(__file__).parent; lib=p/'lib';m=lib/'main.dart'
s=m.read_text(encoding='utf-8')
if 'class Api' in s:
 api=s[:s.index('void main()=>')];api=api.replace("import 'package:flutter/material.dart';\n",'')
 start=api.index('const blue=');end=api.index('const baseUrl=',start);api=api[:start]+api[end:]
 start=api.index('String money(');end=api.index('class Api',start);api=api[:start]+api[end:]
 (lib/'api.dart').write_text(api,encoding='utf-8')
 (lib/'legacy_menu.dart').write_text(s,encoding='utf-8')
 (lib/'main.dart').write_text("import 'relationship.dart' as app;\nexport 'relationship.dart' show Tunibiz, money;\nvoid main()=>app.main();\n",encoding='utf-8')
(p/'test'/'widget_test.dart').write_text("""import 'package:flutter_test/flutter_test.dart';
import 'package:tunibiz_mobile/main.dart';
void main(){
 test('amount is formatted in Tunisian dinars',(){expect(money(3500),'3.500 DT');});
 testWidgets('home exposes both journeys',(tester) async {
  await tester.pumpWidget(const Tunibiz());
  expect(find.text('Espace commerçant'),findsOneWidget);
  expect(find.text('Ma carte fidélité'),findsOneWidget);
 });
}
""",encoding='utf-8')
print('FLUTTER ENTRY SWITCHED')
