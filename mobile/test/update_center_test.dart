import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:tunibiz_mobile/update_center.dart';
void main(){
 test('release metadata agrees with the Android package version',(){
 final declared=RegExp(r'^version:\s+([^\r\n]+)',multiLine:true).firstMatch(File('pubspec.yaml').readAsStringSync())!.group(1);
 expect(declared,'$currentVersion+$currentVersionCode');
 });
 test('only newer official release metadata accepted',(){
 final r=<String,dynamic>{'version':'0.5.1','code':8,'url':'https://github.com/iheb-haouech/TUNIBIZ/releases/download/v0.5.1/TUNIBIZ-v0.5.1.apk','sha256':List.filled(64,'a').join(),'notes':'test'};
 expect(validRelease(r),isTrue);
 expect(validRelease({...r,'code':currentVersionCode}),isFalse);
 expect(validRelease({...r,'url':'https://evil.example/evil.apk'}),isFalse);
 expect(validRelease({...r,'sha256':'bad'}),isFalse);
 expect(validRelease({...r,'version':'0.5.0'}),isFalse);
 });
}
