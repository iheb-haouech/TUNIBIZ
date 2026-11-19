import 'package:flutter_test/flutter_test.dart';
import 'package:tunibiz_mobile/store_scan.dart';
void main(){
 test('only official merchant join URLs accepted',(){
  expect(storeSlug('https://ihebhaouech.pythonanywhere.com/join/store-one'),'store-one');
  expect(storeSlug('https://ihebhaouech.pythonanywhere.com/download'),isNull);
  expect(storeSlug('https://evil.example/join/store-one'),isNull);
  expect(storeSlug('http://ihebhaouech.pythonanywhere.com/join/store-one'),isNull);
  expect(storeSlug('https://ihebhaouech.pythonanywhere.com/join/store-one/other'),isNull);
 });
}
