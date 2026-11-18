# TUNIBIZ — Marketing et fidélisation
Plateforme pour tous les commerces tunisiens. Deux piliers : CRM / marketing et fidélisation.

## Web local
- http://127.0.0.1:8877/ — vitrine FR/EN/AR
- http://127.0.0.1:8877/crm — CRM commerçant
- http://127.0.0.1:8877/loyalty — carte client personnelle
Depuis mvp/: python -m pip install -r requirements.txt ; python app.py
Identifiants de démonstration: mvp/data/demo-login.txt (générés localement, exclus de Git).
Le code historique commandes/menu/réservations reste dans le dépôt mais n'est plus au cœur du produit.

## Parcours MVP
Créer une fiche client (consentement marketing facultatif), remettre son code personnel unique, enregistrer un achat en DT. 1 point par dinar entier par achat, calcul en millimes. Créer une récompense (ex. réduction), débiter les points au comptoir. Publier des campagnes dans les cartes des clients consentants, segment tous / VIP (dépenses >=100 DT) / inactifs (>30 jours). Le code est révocable ; le client peut retirer son consentement. Aucun SMS, email ni WhatsApp envoyé. Pas de paiement ou de remise appliquée automatiquement. Règles temporaires de démonstration.
## Flutter
mobile/lib/main.dart lance les parcours CRM et fidélité. API commune au site. SDK Flutter stable sur SPYKY E:/TUNIBIZ-Dev/flutter. Depuis mobile/: flutter pub get, flutter analyze, flutter test. Créer les plateformes Android avec flutter create --platforms=android --org tn.tunibiz . (préserver les sources), puis lancer avec --dart-define=API_BASE=http://10.0.2.2:8877 pour émulateur ; sur appareil USB adb reverse tcp:8877 tcp:8877 et API_BASE=http://127.0.0.1:8877. HTTP local uniquement pour debug.
## Tests
mvp/test_crm.py et mvp/test_relationship.py couvrent les nouveaux flux ; test_mvp.py couvre l'ancien backend.
## Avant production
Enregistrement multi-commerces, gestion de consentement prouvable, règles personnalisables, protection contre abus, audit sécurité, suppression/export des données, HTTPS, déploiement et sauvegardes, intégration des canaux de communication avec autorisation explicite, tests Android réels. Ne pas exposer le serveur Flask de développement à Internet.
