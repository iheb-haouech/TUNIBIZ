# TUNIBIZ — Google Analytics et Tag Manager

État du 19 novembre 2026. Préparation du déploiement unique ; aucun Reload PythonAnywhere effectué.

## Identifiants utilisés

| Élément | Valeur | Provenance |
|---|---|---|
| Conteneur Web | GTM-N7B5938K | Fourni par le propriétaire |
| Destination GA4 Web | G-HP8K9C7WD5 | Détectée dans le script public de ce conteneur |
| Flux Web | 16374350895 | Capture fournie ; identifiant de flux, différent du G-ID |
| Flux Android | 16373485634 | Capture fournie |
| Projet Firebase | tunibiz-782f0 | Fichier google-services.json existant |
| Package Android | tn.tunibiz.tunibiz_mobile | Configuration existante vérifiée |
| App Firebase Android | 1:900545281118:android:9612375c25e1ace973c8cf | Configuration existante vérifiée |

La correspondance du flux Web affiché dans la console avec G-HP8K9C7WD5 doit être confirmée dans ses détails. Aucun nouveau projet ou flux n'est créé.

## Web développé et testé

- Le code inclut le démarrage GTM correct : dataLayer, gtm.start et événement gtm.js.
- Mode de consentement basique : le chargeur Google apparaît seulement après acceptation. Un choix non bloquant est proposé ; le site fonctionne en refusant.
- analytics_storage est refusé par défaut ; ad_storage, ad_user_data, ad_personalization et personnalisation restent refusés même après acceptation des statistiques.
- Un seul chargeur est injecté. GTM est utilisé lorsque son ID est présent ; gtag.js sert de repli lorsque le conteneur est explicitement désactivé.
- Les événements sont envoyés par gtag à la destination déjà chargée par GTM. L'objet dataLayer `tunibiz_event` permet d'inspecter `tn_event_name`, `tn_page_path` et `tn_platform`.
- Ne pas ajouter une seconde balise GA4 Event sur les mêmes `tunibiz_event` sans retirer cet envoi gtag : cela doublerait la mesure.
- Les paramètres ajoutés par TUNIBIZ sont des noms fonctionnels, un chemin de page fixe et la plateforme. Les query strings, fragments, référents, emails, mots de passe, codes QR, identifiants de compte et positions GPS sont exclus.
- Administration et pages de liens sensibles ne chargent pas Google. Retrait du consentement : désactivation, nettoyage des cookies GA et rechargement conservant la session applicative.
- Les réponses signalant une opération déjà traitée ne produisent pas un second événement de conversion.

Événements couverts : navigation, inscription et connexion, consultation du portefeuille et des vitrines, QR et validations, coupons obtenus/utilisés, promotions/packs créés ou arrêtés, photos, favoris et Nearby. Les noms externes portent le préfixe tn_; page_view garde le nom GA4 standard.

## Android préparé

- Le fichier Firebase existant est conservé sur SPYKY hors Git. Le script de compilation valide le projet et le package, le copie dans le workspace Android et utilise le plugin Google Services 4.6.0.
- Les ressources Android fournissent le véritable google_app_id au SDK Analytics. Les mêmes paramètres publics sont aussi disponibles par définitions Dart, sans clé privée dans l'APK.
- La collecte Analytics et les consentements publicitaires sont refusés par défaut dans le manifeste. Les trois permissions héritées AD_ID / AdServices AD_ID / Attribution sont explicitement retirées du manifeste fusionné.
- Le choix Analytics est conservé chiffré dans le coffre Android, indépendant des comptes commerçant et consommateur.
- Après accord : initialisation/activation Analytics, événements tn_* et noms d'écran fixes. Après retrait : consentement refusé, collecte arrêtée et données Analytics de l'app réinitialisées.
- Aucun nom de client, email, QR, solde de points, identifiant de compte ou GPS n'est transmis par les appels Analytics TUNIBIZ.

La réception Firebase sur téléphone et DebugView reste à vérifier physiquement. Le flux Android affiché « aucune donnée » n'est pas une preuve que l'APK actuel contient déjà cette configuration.

## Validation observée

| Test | Résultat |
|---|---|
| Consentement navigateur | Aucun appel Google avant le choix |
| Après accord | Un chargeur GTM ; un seul page_view |
| URL contenant des valeurs fictives sensibles | Ces valeurs sont absentes des commandes et requêtes Google observées |
| Retrait | Aucun rechargement Google, session portefeuille conservée |
| Routes admin / récupération / confirmation | Aucun chargeur Google |
| SDK Google réel sur copie locale | Deux réponses HTTP 204 |
| Coupon réclamé deux fois | Un seul événement coupon_claimed, réponse de répétition dédupliquée |
| Événements observés | page_view, tn_wallet_view, tn_wallet_open |

[Preuve du test de transport réel](docs/pilot050/google-live-test.json).

Ce test utilise un compte fictif, un site local isolé et le mode debug. Il démontre l'envoi accepté par le collecteur ; il ne démontre pas la réception dans les rapports de la console ni le déploiement sur le site public.

## Configuration de production à appliquer avec le lot global

Variables publiques serveur :

```text
TUNIBIZ_GA4_MEASUREMENT_ID=G-HP8K9C7WD5
TUNIBIZ_GTM_CONTAINER_ID=GTM-N7B5938K
TUNIBIZ_GOOGLE_ANALYTICS_ENABLED=1
```

Mettre TUNIBIZ_GOOGLE_ANALYTICS_ENABLED=0 désactive les destinations Google. Le consentement reste nécessaire lorsque la destination est configurée.

Avant validation commerciale, contrôler dans Google tag / GA4 :
- Que le flux Web sélectionné affiche G-HP8K9C7WD5.
- « Allow user-provided data capabilities » et la détection automatique d'emails/téléphones/adresses : désactivées pour ce pilote.
- Mesure améliorée des formulaires, recherches et liens pouvant contenir des paramètres sensibles : désactivée. TUNIBIZ transmet ses événements fonctionnels explicitement.
- Google Signals et personnalisation publicitaire : désactivés.
- Consentement et événements dans Tag Assistant et DebugView, puis réception Web après le déploiement et Android après installation du candidat signé.

Le script public du conteneur contient actuellement des options de détection automatique activées. Le test réel n'a observé aucun des emails, fragments ou hashes fictifs dans les requêtes testées, avec ad_user_data refusé. Les réglages de la propriété Google ne sont pas modifiés par le code du dépôt ; leur contrôle reste nécessaire.

L'absence de données sur la capture est compatible avec l'ancien site sans destination configurée et l'ancien APK sans ressources Firebase opérationnelles. La version préparée corrige ces deux points ; elle doit être déployée et utilisée avec consentement pour valider les flux réels.

## Références officielles

- [Consentement Web](https://developers.google.com/tag-platform/security/guides/consent)
- [Collecte Firebase Android](https://firebase.google.com/docs/analytics/android/configure-data-collection)
- [Configuration Android Firebase](https://firebase.google.com/docs/android/setup)
- [Identifiant de mesure GA4](https://support.google.com/analytics/answer/12270356)

Le candidat peut être contrôlé localement avec `verify-pilot.ps1` : signature permanente, version/package, app Firebase dans les ressources compilées, refus Analytics/publicité par défaut et absence des permissions publicitaires. Le script n’installe et ne publie rien.
