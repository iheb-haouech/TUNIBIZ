import 'dart:convert';
import 'dart:async';
import 'package:tunibiz_mobile/secure_cache.dart';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:tunibiz_mobile/api.dart';

void main() {
  late HttpServer server;
  late Api api;
  Future<void> serve(Future<void> Function(HttpRequest) handler,
      {Duration timeout = const Duration(seconds: 2)}) async {
    server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    server.listen((request) async {
      try { await handler(request); } catch (_) { /* Client may time out. */ }
    });
    api = Api(scope: 'wallet', serverUrl: 'http://127.0.0.1:${server.port}', requestTimeout: timeout);
    api.signedIn = true;
    api.cookies['session'] = Cookie('session', 'saved-session');
  }
  tearDown(() async { api.close(); await server.close(force: true); });

  test('a temporary HTML hosting failure retains the saved account and cookie', () async {
    await serve((r) async {
      r.response.statusCode = 503;
      r.response.cookies.add(Cookie('session', '')..maxAge = 0);
      r.response.write('<html>private hosting error</html>');
      await r.response.close();
    });
    await expectLater(api.call('/wallet'), throwsA(isA<ApiUnavailable>()));
    expect(api.signedIn, isTrue);
    expect(api.cookies['session']!.value, 'saved-session');
  });
  test('401 from a protected route revokes locally even with a non-JSON body', () async {
    await serve((r) async { r.response.statusCode = 401; r.response.write('Unauthorized'); await r.response.close(); });
    await expectLater(api.call('/wallet'), throwsA(isA<SessionExpired>()));
    expect(api.signedIn, isFalse); expect(api.cookies, isEmpty);
  });
  test('a rejected login does not discard an existing saved account', () async {
    await serve((r) async { r.response.statusCode = 401; r.response.write(jsonEncode({'error': 'Identifiants incorrects'})); await r.response.close(); });
    await expectLater(api.call('/wallet/login', {'password': 'incorrect'}), throwsA(isA<ApiUnavailable>()));
    expect(api.signedIn, isTrue); expect(api.cookies['session']!.value, 'saved-session');
  });
  test('a malformed successful response has a readable error and retains the session', () async {
    await serve((r) async { r.response.write('[invalid'); await r.response.close(); });
    await expectLater(api.call('/wallet'), throwsA(isA<ApiUnavailable>()));
    expect(api.signedIn, isTrue);
  });
  test('a response body that stops arriving is bounded by a total deadline', () async {
    await serve((r) async {
      r.response.write('{'); await r.response.flush();
      await Future<void>.delayed(const Duration(milliseconds: 400));
      r.response.write('}'); await r.response.close();
    }, timeout: const Duration(milliseconds: 120));
    final elapsed = Stopwatch()..start();
    await expectLater(api.call('/wallet'), throwsA(isA<ApiUnavailable>()));
    expect(elapsed.elapsedMilliseconds, lessThan(350));
    expect(api.signedIn, isTrue);
  });
  test('oversized bodies are refused while the account remains available', () async {
    await serve((r) async { r.response.contentLength = Api.maxResponseBytes + 1; r.response.write('x'); await r.response.flush(); });
    await expectLater(api.call('/wallet'), throwsA(isA<ApiUnavailable>()));
    expect(api.signedIn, isTrue);
  });
  test('redirects are not followed and do not replace saved sessions', () async {
    await serve((r) async { r.response.statusCode = 302; r.response.headers.set('location', '/elsewhere'); await r.response.close(); });
    await expectLater(api.call('/wallet'), throwsA(isA<ApiUnavailable>()));
    expect(api.cookies['session']!.value, 'saved-session');
  });
  test('valid data updates the session and successful logout clears it', () async {
    await serve((r) async {
      r.response.cookies.add(Cookie('session', 'renewed-session'));
      r.response.write(jsonEncode({'ok': true, 'profile': {'name': 'QA'}}));
      await r.response.close();
    });
    expect((await api.call('/wallet'))['ok'], isTrue);
    expect(api.cookies['session']!.value, 'renewed-session');
    await api.call('/wallet/logout', {});
    expect(api.signedIn, isFalse); expect(api.cookies, isEmpty);
  });
  test('server denial never resurrects a cached private response', () async {
    var requests=0;
    await serve((r) async {
      requests++;
      r.response.statusCode=requests==1?200:403;
      r.response.write(requests>2?'<html>Forbidden</html>':jsonEncode(requests==1?{'private':'TEST'}:{'error':'Access denied'}));
      await r.response.close();
    });
    expect((await api.cached('/restricted'))['private'],'TEST');
    await expectLater(api.cached('/restricted'),throwsA(isA<ApiUnavailable>().having((e)=>e.cacheable,'cacheable',false)));
    await expectLater(api.cached('/restricted'),throwsA(isA<ApiUnavailable>().having((e)=>e.cacheable,'cacheable',false)));
  });

  test('local sign-out completes without waiting for server revocation, retaining old request scope',()async{
    final started=Completer<Map<String,String>>(),release=Completer<void>(),finished=Completer<void>();
    await serve((r)async{
      started.complete({'cookie':r.headers.value('cookie')??'','csrf':r.headers.value('X-CSRF-Token')??''});
      await release.future;r.response.write('{}');await r.response.close();finished.complete();
    });
    api.csrf='old-csrf';await SecureCache.put('wallet','/wallet',{'private':'TEST'});
    await api.signOut('/wallet/logout');
    expect(api.signedIn,false);expect(api.cookies,isEmpty);expect(await SecureCache.read('wallet','/wallet'),isNull);
    final request=await started.future.timeout(const Duration(seconds:5));
    expect(request['cookie'],contains('saved-session'));expect(request['csrf'],'old-csrf');
    release.complete();await finished.future;
  });
  test('in-flight response cannot resurrect cookies or private cache after logout',()async{
    final started=Completer<void>(),release=Completer<void>();
    await serve((r)async{
      started.complete();await release.future;
      r.response.cookies.add(Cookie('session','stale-session'));
      r.response.write(jsonEncode({'private':'OLD ACCOUNT'}));await r.response.close();
    });
    final response=api.cached('/wallet');await started.future;await api.clearLocal();release.complete();
    await expectLater(response,throwsA(isA<ApiUnavailable>().having((e)=>e.cacheable,'cacheable',false)));
    expect(api.signedIn,false);expect(api.cookies,isEmpty);expect(await SecureCache.read('wallet','/wallet'),isNull);
  });

}
