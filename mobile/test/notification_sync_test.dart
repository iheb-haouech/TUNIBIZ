import 'dart:async';
import 'package:flutter_test/flutter_test.dart';
import 'package:tunibiz_mobile/notification_sync.dart';
import 'package:tunibiz_mobile/api.dart';
class NoticeApi extends Api {
 Map<String,dynamic> data={'notifications':[{'id':21}]};bool fail=false;Completer<void>? pending,started;
 NoticeApi(){signedIn=true;}
 @override Future<Map<String,dynamic>> call(String path,[Map<String,dynamic>? body])async{
  expect(path,'/commerce/profile');started?.complete();await pending?.future;
  if(fail)throw const ApiUnavailable('offline');return data;
 }
}
void main(){
 test('cloud hints require authenticated server records and active consent',()async{
  final api=NoticeApi();addTearDown(api.close);var allowed=true,refreshes=0;final shown=<String>[];
  final sync=ConfirmedNotificationSync(api:api,refresh:()async{refreshes++;},allowed:()async=>allowed,show:(id)async{shown.add(id);});
  api.fail=true;await sync.receive();expect(shown,isEmpty);expect(refreshes,0);
  api.fail=false;api.data={'notifications':[]};await sync.receive();expect(shown,isEmpty);
  api.data={'notifications':[{'id':21}]};allowed=false;await sync.receive();expect(shown,isEmpty);
  allowed=true;await sync.receive();expect(shown,['notice:21']);
 });
 test('logout during an in-flight cloud refresh cannot notify the next account',()async{
  final api=NoticeApi()..pending=Completer<void>()..started=Completer<void>();addTearDown(api.close);final shown=<String>[];
  final sync=ConfirmedNotificationSync(api:api,refresh:()async{},allowed:()async=>true,show:(id)async{shown.add(id);});
  final pending=sync.receive();await api.started!.future;await api.clearLocal();api.signedIn=true;api.pending!.complete();await pending;expect(shown,isEmpty);
 });
 test('revoking consent while refresh finishes suppresses notification',()async{
  final api=NoticeApi();addTearDown(api.close);var consent=true;final shown=<String>[];
  final sync=ConfirmedNotificationSync(api:api,refresh:()async{consent=false;},allowed:()async=>consent,show:(id)async{shown.add(id);});
  await sync.receive();expect(shown,isEmpty);
 });
}
