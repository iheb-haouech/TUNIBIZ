import 'dart:async';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:tunibiz_mobile/api.dart';
class DelayedClient implements HttpClient {
 final inner=HttpClient(),started=Completer<void>(),release=Completer<void>();
 @override Future<HttpClientRequest> openUrl(String method,Uri url)async{final request=await inner.openUrl(method,url);started.complete();await release.future;return request;}
 @override void close({bool force=false})=>inner.close(force:force);
 @override dynamic noSuchMethod(Invocation invocation)=>super.noSuchMethod(invocation);
}
class IdentityApi extends Api {
 final delayed=DelayedClient();IdentityApi(String origin):super(scope:'wallet',serverUrl:origin);
 @override HttpClient get client=>delayed;
}
void main(){
 test('an operation queued before logout is not sent with a new session',()async{
  final server=await HttpServer.bind(InternetAddress.loopbackIPv4,0);var mutations=0;
  server.listen((r)async{mutations++;r.response.write('{}');await r.response.close();});
  final api=IdentityApi('http://127.0.0.1:${server.port}');addTearDown(()=>server.close(force:true));addTearDown(api.close);
  api.signedIn=true;api.csrf='old';api.cookies['session']=Cookie('session','old');
  final request=api.call('/operation',{'points':20});await api.delayed.started.future;
  await api.clearLocal();api.cookies['session']=Cookie('session','new');api.csrf='new';api.signedIn=true;
  api.delayed.release.complete();await expectLater(request,throwsA(isA<ApiUnavailable>()));await Future<void>.delayed(const Duration(milliseconds:50));expect(mutations,0);
 });
}
