import 'dart:convert';
import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/foundation.dart';
import 'usage_analytics.dart';
import 'session_vault.dart';
import 'secure_cache.dart';

const baseUrl = String.fromEnvironment('API_BASE', defaultValue: 'https://ihebhaouech.pythonanywhere.com');
class SessionExpired implements Exception {
  @override
  String toString() => 'Session expiree. Reconnectez-vous.';
}
class ApiUnavailable implements Exception {
  final String message;
  const ApiUnavailable(this.message);
  @override
  String toString() => message;
}
class Api {
  final String? scope;
  final String serverUrl;
  final Duration requestTimeout;
  final HttpClient client;
  bool restored = false, signedIn = false;
  // A response is bounded even when the hosting proxy streams slowly or sends HTML.
  static const maxResponseBytes = 2 * 1024 * 1024;
  Api({this.scope, String? serverUrl, HttpClient? httpClient,
      this.requestTimeout = const Duration(seconds: 15)})
      : serverUrl = serverUrl ?? baseUrl,
        client = httpClient ?? (HttpClient()..connectionTimeout = const Duration(seconds: 10));
  final Map<String, Cookie> cookies = {};
  String csrf = '';
  Future<void> clearLocal() async {
    signedIn = false;
    cookies.clear();
    csrf = '';
    await SecureCache.clear(scope);
    if (scope != null) await SessionVault.write(scope!, null);
  }
  bool _expired(String path, int status) => status == 401 &&
      ((scope == 'wallet' && (['/wallet', '/wallet/store-scan', '/wallet/store-scans'].contains(path) || path == '/commerce/profile')) ||
       (scope == 'merchant' && (path == '/crm' || path.startsWith('/commerce/')))  ||
       (scope == 'legacy' && path == '/loyalty'));
  Future<String> _body(HttpClientResponse response) async {
    if (response.contentLength > maxResponseBytes) {
      throw const ApiUnavailable('Réponse serveur trop volumineuse. Réessayez plus tard.');
    }
    final input = StreamIterator<List<int>>(response);
    final bytes = BytesBuilder(copy: false);
    final clock = Stopwatch()..start();
    try {
      while (true) {
        final left = requestTimeout - clock.elapsed;
        if (left <= Duration.zero) throw TimeoutException('response');
        if (!await input.moveNext().timeout(left)) break;
        if (bytes.length + input.current.length > maxResponseBytes) {
          throw const ApiUnavailable('Réponse serveur trop volumineuse. Réessayez plus tard.');
        }
        bytes.add(input.current);
      }
      return utf8.decode(bytes.takeBytes());
    } finally {
      await input.cancel();
    }
  }
  Future<Map<String, dynamic>> call(String path, [Map<String, dynamic>? body]) async {
    if (kReleaseMode && (!serverUrl.startsWith('https://') || Uri.tryParse(serverUrl)?.host.isEmpty != false)) {
      throw StateError('Serveur HTTPS de production non configure');
    }
    HttpClientRequest? req;
    try {
      req = await client.openUrl(body == null ? 'GET' : 'POST', Uri.parse(serverUrl + '/api' + path)).timeout(requestTimeout);
      req.followRedirects = false;
      if (UsageAnalytics.allowed) {
        req.headers.set('X-Tunibiz-Analytics', 'yes');
        req.headers.set('X-Tunibiz-Platform', 'android');
      }
      req.cookies.addAll(cookies.values);
      if (body != null) {
        req.headers.contentType = ContentType.json;
        req.headers.set('X-CSRF-Token', csrf);
        req.write(jsonEncode(body));
      }
      final res = await req.close().timeout(requestTimeout);
      // Revocation remains authoritative even if a proxy replaces the JSON body.
      if (_expired(path, res.statusCode)) {
        await clearLocal();
        req.abort();
        throw SessionExpired();
      }
      if (res.statusCode >= 300 && res.statusCode < 400) {
        req.abort();
        throw const ApiUnavailable('Redirection serveur refusée');
      }
      final raw = await _body(res);
      Map<String, dynamic>? decoded;
      try {
        final value = jsonDecode(raw);
        if (value is Map<String, dynamic>) decoded = value;
      } on FormatException { /* HTML and malformed JSON are never shown to users. */ }
      if (decoded == null) {
        throw const ApiUnavailable('Serveur temporairement indisponible. Réessayez dans un instant.');
      }
      if (res.statusCode >= 400) {
        final error = decoded['error'];
        if (res.statusCode >= 500 || error is! String || error.length > 500) {
          throw const ApiUnavailable('Serveur temporairement indisponible. Réessayez dans un instant.');
        }
        throw ApiUnavailable(error);
      }
      // Do not replace a saved session on network/proxy errors.
      for (final c in res.cookies) {
        if (c.maxAge == 0) { cookies.remove(c.name); } else { cookies[c.name] = c; }
      }
      if (scope != null) {
        if (['/wallet/login', '/wallet/register', '/google/login', '/login', '/loyalty/login'].contains(path)) {await SecureCache.clear(scope);signedIn = true;}
        if (['/wallet/logout', '/wallet/delete', '/logout'].contains(path) || (path == '/loyalty/logout' && scope == 'legacy')) {
          await clearLocal();
        } else if (signedIn && cookies['session'] != null) {
          await SessionVault.write(scope!, cookies['session']!.value);
        }
      }
      final event = res.headers.value('X-Tunibiz-Event');
      if (event != null) unawaited(UsageAnalytics.log(event));
      return decoded;
    } on TimeoutException {
      req?.abort();
      throw const ApiUnavailable('Connexion trop lente. Vérifiez Internet puis réessayez.');
    } on SocketException {
      req?.abort();
      throw const ApiUnavailable('Connexion Internet indisponible. Votre compte reste enregistré.');
    } on HttpException {
      req?.abort();
      throw const ApiUnavailable('Connexion interrompue. Réessayez dans un instant.');
    } on FormatException {
      req?.abort();
      throw const ApiUnavailable('Réponse serveur invalide. Réessayez dans un instant.');
    } on ApiUnavailable {
      req?.abort();
      rethrow;
    }
  }
  Future<bool> restore() async {
    if (!restored) {
      restored = true;
      if (scope != null && serverUrl.startsWith('https://')) {
        final saved = await SessionVault.read(scope!);
        if (saved != null) { cookies['session'] = Cookie('session', saved); signedIn = true; }
      }
    }
    return signedIn;
  }
  Future<Map<String,dynamic>> cached(String path)async{
    if(!path.startsWith('/')||path.startsWith('/admin'))throw ArgumentError('Cache path');
    try{final data=await call(path);await SecureCache.put(scope,path,data);return data;}
    on ApiUnavailable {final data=await SecureCache.read(scope,path);if(data!=null)return data;rethrow;}
  }
  Future<void> init() async {
    await restore();
    final result = await call('/session');
    final value = result['csrf'];
    if (value is! String || value.isEmpty) throw const ApiUnavailable('Session serveur indisponible. Réessayez.');
    csrf = value;
  }
  static Future<void> usage(String event) async {
    if (!UsageAnalytics.allowed) return;
    final a = Api();
    try {
      await a.init();
      if (!UsageAnalytics.allowed) return;
      await a.call('/analytics/event', {'event': event});
      await UsageAnalytics.log(event);
    } catch (_) { } finally { a.close(); }
  }
  void close() => client.close(force: true);
}
