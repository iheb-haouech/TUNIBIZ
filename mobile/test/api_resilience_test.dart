import 'dart:convert';
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
}
