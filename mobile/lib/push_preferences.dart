import 'dart:async';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'api.dart';
import 'session_vault.dart';

/// Opt-in only; notification text does not contain account or purchase details.
class PushPreferences extends StatefulWidget {
  final Api api;
  const PushPreferences({super.key, required this.api});
  static bool supported(Api api) => SessionVault.available && api.serverUrl.startsWith('https://');
  static Future<void> clearConsent(Api api) async {
    if (!supported(api)) return;
    await SessionVault.write('push_consent', null);
    try {
      if (Firebase.apps.isEmpty) await Firebase.initializeApp();
      final f = FirebaseMessaging.instance;
      await f.setAutoInitEnabled(false);
      await f.deleteToken();
    } catch (_) { }
  }
  @override
  State<PushPreferences> createState() => _PushPreferencesState();
}

class _PushPreferencesState extends State<PushPreferences> {
  bool enabled = false, busy = true;
  String status = '';
  StreamSubscription<String>? changes;
  @override
  void initState() {
    super.initState();
    unawaited(restore());
  }
  @override
  void dispose() {
    changes?.cancel();
    super.dispose();
  }
  Future<FirebaseMessaging> messaging() async {
    if (Firebase.apps.isEmpty) await Firebase.initializeApp();
    return FirebaseMessaging.instance;
  }
  Future<String> device() async {
    final old = await SessionVault.read('push_device');
    if (old != null && RegExp(r'^[a-f0-9]{32}$').hasMatch(old)) return old;
    final rng = Random.secure();
    final id = List.generate(16, (_) => rng.nextInt(256).toRadixString(16).padLeft(2,'0')).join();
    await SessionVault.write('push_device', id);
    return id;
  }
  Future<void> register(String token) async {
    if (!mounted || !widget.api.signedIn || await SessionVault.read('push_consent') != 'yes') return;
    await widget.api.call('/push/register', {'device_id': await device(), 'token': token, 'consent': true});
  }
  Future<void> sync(FirebaseMessaging f) async {
    await f.setAutoInitEnabled(true);
    final token = await f.getToken();
    if (token == null) throw StateError('Notifications indisponibles');
    await register(token);
    if (!mounted) return;
    await changes?.cancel();
    changes = f.onTokenRefresh.listen((token) async {
      try { await register(token); } catch (_) { }
    });
  }
  Future<void> restore() async {
    try {
      if (await SessionVault.read('push_consent') == 'yes') {
        final f = await messaging();
        if ((await f.getNotificationSettings()).authorizationStatus == AuthorizationStatus.authorized) {
          await sync(f);
          enabled = true;
        } else {
          await unregister();
          await PushPreferences.clearConsent(widget.api);
        }
      }
    } catch (_) { status = 'Notifications temporairement indisponibles.'; }
    finally { if (mounted) setState(() => busy = false); }
  }
  Future<void> unregister() async {
    final id = await SessionVault.read('push_device');
    if (id != null && widget.api.signedIn) await widget.api.call('/push/unregister', {'device_id': id});
  }
  Future<void> change(bool value) async {
    setState(() { busy = true; status = ''; });
    try {
      if (value) {
        final f = await messaging();
        final settings = await f.requestPermission(alert: true, badge: true, sound: true);
        if (settings.authorizationStatus != AuthorizationStatus.authorized) {
          status = 'Autorisation Android refusee.';
          return;
        }
        await SessionVault.write('push_consent', 'yes');
        try { await sync(f); enabled = true; }
        catch (_) {
          await PushPreferences.clearConsent(widget.api);
          rethrow;
        }
      } else {
        await changes?.cancel();
        changes = null;
        await PushPreferences.clearConsent(widget.api);
        enabled = false;
        await unregister();
      }
    } catch (_) { status = 'Connexion indisponible. Reessayez.'; }
    finally { if (mounted) setState(() => busy = false); }
  }
  @override
  Widget build(BuildContext context) => Column(children: [
    SwitchListTile(
      secondary: const Icon(Icons.notifications_outlined),
      title: const Text('Notifications du portefeuille'),
      subtitle: const Text('Alertes facultatives sur les achats et validations.'),
      value: enabled, onChanged: busy ? null : change),
    if (status.isNotEmpty) Text(status),
  ]);
}
