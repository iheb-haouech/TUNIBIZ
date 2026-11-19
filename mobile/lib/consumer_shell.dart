import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'api.dart';
import 'nearby.dart';
import 'premium.dart';
import 'session_vault.dart';
import 'storefront.dart';
import 'update_center.dart';
import 'usage_analytics.dart';
import 'wallet.dart';

/// One account and one set of tab states survive consumer navigation.
class ConsumerShell extends StatefulWidget {
  final CardBuilder cardBuilder;
  final Widget Function() businessBuilder;
  final Api? apiOverride;
  final Future<String?> Function(BuildContext)? scannerOverride;
  const ConsumerShell({super.key, required this.cardBuilder, required this.businessBuilder,
    this.apiOverride, this.scannerOverride});
  @override
  State<ConsumerShell> createState() => _ConsumerShellState();
}
class _ConsumerShellState extends State<ConsumerShell> {
  static const permissions = MethodChannel('tn.tunibiz/nearby');
  late final api = widget.apiOverride ?? Api(scope: 'wallet');
  final walletController = ConsumerWalletController();
  final visited = <int>{0};
  int index = 0;
  bool loading = false;
  String error = '';
  Map<String, dynamic>? wallet;
  List<Map<String, dynamic>> stores = [], offers = [];
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => startup());
  }
  @override
  void dispose() {
    walletController.dispose();
    if (widget.apiOverride == null) api.close();
    super.dispose();
  }
  Future<void> startup() async {
    if(SessionVault.available)await UsageAnalytics.restore();
    await load();
    if(UsageAnalytics.allowed){await UsageAnalytics.screen('home');unawaited(Api.usage('home_view'));}
    if (!mounted || !SessionVault.available || !baseUrl.startsWith('https://')) return;
    try {
      if (await permissions.invokeMethod<bool>('onboardingNeeded') == true && mounted) {
        final allow = await showDialog<bool>(context: context, builder: (ctx) => AlertDialog(
          title: const Text('Bienvenue sur TUNIBIZ'),
          content: const Text('La localisation approximative sert à découvrir les offres Nearby. Les notifications sont facultatives. Vous pouvez refuser et garder votre portefeuille et le scanner QR.'),
          actions: [TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Plus tard')),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Configurer'))]));
        if (allow == true) {
          await permissions.invokeMethod<bool>('permissionNotifications');
          if (mounted) await permissions.invokeMethod<bool>('permissionLocation');
        }
        await permissions.invokeMethod('onboardingDone');
      }
    } catch (_) { /* Optional permissions never block the wallet. */ }
    if(mounted&&await SessionVault.read('analytics')==null&&mounted){
      final choice=await UsageAnalytics.preferences(context);
      if(choice!=null){await UsageAnalytics.change(choice);if(choice){await UsageAnalytics.screen('home');unawaited(Api.usage('home_view'));}}
    }
  }
  Future<void> load() async {
    if (loading || !mounted) return;
    setState(() { loading = true; error = ''; if (!api.signedIn) wallet = null; });
    try {
      await api.init();
      Map<String, dynamic>? profile;
      if (api.signedIn) {
        try { profile = await api.call('/wallet'); } on SessionExpired { profile = null; }
      }
      final directory = await api.call('/stores');
      final items = (directory['stores'] as List).map((s) => Map<String, dynamic>.from(s)).toList();
      final feed = <Map<String, dynamic>>[];
      // Bounded real storefront requests; an unavailable commerce does not hide others.
      for (final store in items.take(3)) {
        try {
          final detail = await api.call('/stores/${store['id']}');
          for (final offer in (detail['offers'] as List? ?? []).take(2)) {
            feed.add({...Map<String, dynamic>.from(offer), 'shop_name': store['name'], 'shop_id': store['id']});
          }
        } catch (_) { }
      }
      if (mounted) setState(() { wallet = profile; stores = items; offers = feed; });
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }
  void select(int next) {
    FocusManager.instance.primaryFocus?.unfocus();
    final destination = next == 2 ? 4 : next;
    if(next!=index){unawaited(UsageAnalytics.screen(const ['home','stores','scanner','nearby','wallet'][next]));unawaited(Api.usage(const ['home_view','stores_open','wallet_open','nearby_open','wallet_open'][next]));}
    if (next == 2) walletController.requestScan();
    setState(() { index = destination; visited.add(destination); });
    if (destination == 0) load();
  }
  Widget home() {
    final profile = wallet?['profile'] as Map?;
    final cards = wallet?['cards'] as List? ?? [];
    return Scaffold(backgroundColor: paper,
      appBar: AppBar(title: const Text('TUNIBIZ'), actions: [
        IconButton(tooltip: 'Actualiser', onPressed: loading ? null : load, icon: const Icon(Icons.refresh)),
        IconButton(tooltip: 'Espace commerçant', onPressed: () => Navigator.push(context,
          MaterialPageRoute(builder: (_) => widget.businessBuilder())), icon: const Icon(Icons.storefront_outlined))]),
      body: RefreshIndicator(onRefresh: load, child: ListView(padding: const EdgeInsets.all(18), children: [
        if (loading) const LinearProgressIndicator(),
        if (error.isNotEmpty) Padding(padding: const EdgeInsets.symmetric(vertical: 10), child: Text(error, style: const TextStyle(color: Colors.red))),
        Container(padding: const EdgeInsets.all(24), decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [ink, Color(0xFF174158)]), borderRadius: BorderRadius.circular(24)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            const Text('VOS COMMERCES. VOS AVANTAGES.', style: TextStyle(color: mint, fontSize: 11, letterSpacing: 1.5, fontWeight: FontWeight.bold)),
            const SizedBox(height: 14),
            Text(profile == null ? 'Le commerce local vous récompense.' : 'Bonjour ${profile['name']}',
              style: const TextStyle(color: Colors.white, fontSize: 29, fontWeight: FontWeight.w800)),
            const SizedBox(height: 12),
            Text(profile == null ? 'Un compte gratuit pour vos cartes de fidélité, vos coupons et les offres proches.' : '${cards.length} carte(s) de fidélité. Vos points restent propres à chaque commerce.', style: const TextStyle(color: Colors.white70)),
            const SizedBox(height: 20),
            FilledButton.icon(onPressed: () => select(2), icon: const Icon(Icons.qr_code_scanner), label: const Text('Scanner un commerce')),
            TextButton(onPressed: () => select(4), child: Text(profile == null ? 'Ouvrir mon portefeuille' : 'Voir mes cartes', style: const TextStyle(color: mint)))
          ])),
        if (cards.isNotEmpty) ...[
          const SizedBox(height: 24), const Text('Mes commerces', style: TextStyle(fontSize: 23, fontWeight: FontWeight.w800, color: ink)),
          for (final card in cards.take(4)) Card(child: ListTile(
            leading: const Icon(Icons.loyalty_outlined, color: cobalt),
            title: Text(card['shop'].toString()), subtitle: Text(card['archived'] == 1 ? 'Commerce archivé · points conservés' : card['city'].toString()),
            trailing: Text('${card['points']} pts', style: const TextStyle(fontWeight: FontWeight.bold, color: cobalt)), onTap: () => select(4)))
        ],
        const SizedBox(height: 24),
        Row(children: [const Expanded(child: Text('À découvrir', style: TextStyle(fontSize: 23, fontWeight: FontWeight.w800, color: ink))),
          TextButton(onPressed: () => select(1), child: const Text('Tout voir'))]),
        if (!loading && stores.isEmpty) const Padding(padding: EdgeInsets.symmetric(vertical: 16), child: Text('Les établissements actifs apparaîtront ici.')),
        for (final store in stores.take(3)) Padding(padding: const EdgeInsets.only(bottom: 12), child: Card(clipBehavior: Clip.antiAlias,
          child: InkWell(onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => StorePage(api: api, id: store['id'] as int))),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [StoreImage(store['cover'], height: 140),
              ListTile(title: Text(store['name'].toString(), style: const TextStyle(fontWeight: FontWeight.bold)), subtitle: Text(store['city'].toString()), trailing: const Icon(Icons.chevron_right))])))),
        if (offers.isNotEmpty) ...[const SizedBox(height: 12), const Text('Offres à découvrir', style: TextStyle(fontSize: 23, fontWeight: FontWeight.w800, color: ink)),
          for (final offer in offers.take(4)) Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Padding(padding: const EdgeInsets.only(top: 12), child: Text(offer['shop_name'].toString(), style: const TextStyle(fontWeight: FontWeight.bold))),
            StoreListing(offer: offer, action: TextButton(onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => StorePage(api: api, id: offer['shop_id'] as int))), child: const Text('Voir dans la vitrine')))])],
        const SizedBox(height: 14),
        OutlinedButton.icon(onPressed: () => select(3), icon: const Icon(Icons.radar), label: const Text('Découvrir les offres Nearby')),
        const SizedBox(height: 14), const UpdateEntry(),
        TextButton(onPressed: () async { final value = await UsageAnalytics.preferences(context); if (value != null) {await UsageAnalytics.change(value);if(value){await UsageAnalytics.screen(const ['home','stores','scanner','nearby','wallet'][index]);unawaited(Api.usage(const ['home_view','stores_open','wallet_open','nearby_open','wallet_open'][index]));}} }, child: const Text('Préférences de statistiques')),
        const Text('Compte consommateur gratuit · Points séparés par commerce.', style: TextStyle(color: muted, fontSize: 12)), const SizedBox(height: 16)
      ])));
  }
  @override
  Widget build(BuildContext context) => PopScope(canPop: index == 0,
    onPopInvokedWithResult: (didPop, _) { if (!didPop) select(0); },
    child: Scaffold(body: IndexedStack(index: index, children: [
      TickerMode(enabled: index == 0, child: home()),
      visited.contains(1) ? TickerMode(enabled: index == 1, child: StoresPage(api: api)) : const SizedBox(),
      const SizedBox(),
      visited.contains(3) ? TickerMode(enabled: index == 3, child: Nearby(apiOverride: api, active: index == 3)) : const SizedBox(),
      visited.contains(4) ? TickerMode(enabled: index == 4, child: ConsumerWallet(apiOverride: api, controller: walletController,
        active: index == 4, scannerOverride: widget.scannerOverride, cardBuilder: widget.cardBuilder)) : const SizedBox()
    ]), bottomNavigationBar: NavigationBar(backgroundColor: Colors.white, indicatorColor: const Color(0xFFE1F9F5),
      selectedIndex: index, onDestinationSelected: select, labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
      destinations: const [
        NavigationDestination(icon: Icon(Icons.home_outlined), label: 'Accueil'),
        NavigationDestination(icon: Icon(Icons.storefront_outlined), label: 'Établissements'),
        NavigationDestination(icon: CircleAvatar(backgroundColor: cobalt, foregroundColor: Colors.white, child: Icon(Icons.qr_code_scanner)), label: 'Scanner'),
        NavigationDestination(icon: Icon(Icons.radar), label: 'Nearby'),
        NavigationDestination(icon: Icon(Icons.account_balance_wallet_outlined), label: 'Portefeuille')
      ])));
}
