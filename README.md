# TUNIBIZ — Your Business. Smarter.

MVP national tunisien. Site + API Flask/SQLite : mvp/. Application Flutter Android : mobile/. Le dossier video/ est une archive locale non versionnée.

## Lancer le site
Depuis VS Code, tâche TUNIBIZ: backend localhost, ou cd mvp puis python -m pip install -r requirements.txt et python app.py.

- http://127.0.0.1:8877/ : site
- http://127.0.0.1:8877/business : commerçant
- http://127.0.0.1:8877/menu/demo : menu client

Les identifiants de démonstration sont générés localement au premier lancement dans mvp/data/demo-login.txt. Ne pas publier les données, secrets ou mots de passe.

## Flutter
SDK Flutter stable requis. Sous Windows SPYKY: E:/TUNIBIZ-Dev/flutter/bin/flutter.bat. Le backend doit tourner avant l'application.

Depuis mobile/: flutter pub get ; flutter analyze ; flutter test ; flutter run --dart-define=API_BASE=http://10.0.2.2:8877 (émulateur Android).
Sur téléphone USB de développement: adb reverse tcp:8877 tcp:8877 puis flutter run --dart-define=API_BASE=http://127.0.0.1:8877.
HTTP local uniquement en debug; production HTTPS et authentification renforcée requises. Les cookies de session sont conservés en mémoire.

## Périmètre
Prototype local en français: catalogue, commandes, réservations, ventes clôturées. Pas encore de paiement, inscription multi-commerces, fidélité, stock ou notification push. Pas de diffusion publique avant audit de sécurité et hébergement.
