import 'package:flutter_test/flutter_test.dart';
import 'package:tunibiz_mobile/checkout_scanner.dart';
void main(){
 test('checkout scanner accepts only the temporary token format',(){
  expect(validCheckoutToken('TNB1:abcdefghijklmnopqrstuvwx'),isTrue);
  expect(validCheckoutToken('https://example.com'),isFalse);
  expect(validCheckoutToken('TNB1:short'),isFalse);
  expect(validCheckoutToken('TNB1:abcdefghijklmnopqrstuvwx!'),isFalse);
 });
}
