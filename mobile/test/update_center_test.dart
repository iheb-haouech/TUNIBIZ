import 'package:flutter_test/flutter_test.dart';
import 'package:tunibiz_mobile/update_center.dart';
void main(){
 test('only newer official release metadata accepted',(){
 final r=<String,dynamic>{'version':'0.4.3','code':7,'url':'https://github.com/iheb-haouech/TUNIBIZ/releases/download/v0.4.3/TUNIBIZ-v0.4.3.apk','sha256':List.filled(64,'a').join(),'notes':'test'};
 expect(validRelease(r),isTrue);
 expect(validRelease({...r,'code':6}),isFalse);
 expect(validRelease({...r,'url':'https://evil.example/evil.apk'}),isFalse);
 expect(validRelease({...r,'sha256':'bad'}),isFalse);
 expect(validRelease({...r,'version':'0.5.0'}),isFalse);
 });
}
