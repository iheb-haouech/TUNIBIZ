# Déploiement unique TUNIBIZ V0.5.0 — procédure préparée, non exécutée

Cette procédure nécessite la validation explicite du propriétaire après les essais Android et la levée des points P0/P1 du rapport. Ne pas utiliser les comptes réels pour la recette. Aucun reload ne fait partie des travaux préparatoires.

## Avant la fenêtre de déploiement

1. Lire `PILOT_V0.5.0_REPORT.md` et les résultats joints. Confirmer le SHA de la branche revue, la version candidate Android et le certificat permanent.
2. Tester l'envoi email, la confirmation et la récupération avec une adresse de test. Ne pas désactiver la vérification email pour masquer un problème de configuration.
3. Sur PythonAnywhere, vérifier Python 3.11 minimum, environnement virtuel, WSGI, données persistantes et quota. Les paquets Windows du poste ne prouvent pas une installation Linux réussie.
4. Préparer un environnement virtuel neuf à partir de `mvp/requirements.lock`. Conserver l'ancien environnement. Le verrou contient les versions testées ; vérifier leur installation sur PythonAnywhere avant bascule.
5. Configurer dans les fichiers privés serveur les variables requises ; ne pas afficher leurs valeurs. Conserver le secret Flask existant. Utiliser `python mvp/pilot_preflight.py` : il n'affiche que des états de présence, versions, intégrité et espace libre. Il n'envoie pas d'emails.
6. Noter les chemins du code, du venv et du fichier WSGI actuels, ainsi que le SHA déployé. Mettre une copie privée du WSGI à l'abri.
7. Vérifier que les accès Google et SMTP HTTPS nécessaires sont autorisés par le plan PythonAnywhere. Un indicateur configuré n'est pas un test réel de livraison.

## Fenêtre unique après approbation

1. Suspendre les écritures pendant la bascule : ne pas laisser d'anciens workers accepter des validations durant les migrations. Une simple copie de la base ouverte n'est pas une sauvegarde fiable.
2. Lancer `python3.11 mvp/backup_db.py` depuis l'environnement existant : la procédure utilise SQLite Backup API et vérifie l'intégrité. Conserver le snapshot hors du dépôt et une copie chiffrée hors de l'hébergement.
3. Restaurer ce snapshot dans un répertoire de contrôle séparé et vérifier `PRAGMA integrity_check` et `PRAGMA foreign_key_check`. Ne pas publier cette copie.
4. Préparer un nouveau répertoire de code au SHA validé depuis `pilot/v0.5.0-20261119`. Ne pas écraser un répertoire avec des modifications non sauvegardées.
5. Dans un processus de maintenance unique, avec la configuration privée de production et le nouveau venv, importer l'application une fois pour appliquer les migrations. Ce démarrage écrit le schéma et les migrations ; il doit se faire pendant la suspension des écritures.
6. Exécuter les tests sur une copie distincte des données, sans compte réel ni envoi marketing ; vérifier le précontrôle sur la cible.
7. Pointer le WSGI vers le code et le venv validés. Effectuer alors un seul Reload de bascule.
8. Contrôler HTTPS, accès admin refusé sans session, portefeuille test, nouvelle inscription confirmée, scan du commerce test, double validation, coupon unique, date d'expiration et absence de données d'un autre commerce.
9. Réouvrir les écritures uniquement après succès. Relever les erreurs et l'espace disque sans journaliser corps de requêtes, cookies ou secrets.
10. Après validation du téléphone, publier un seul APK signé approuvé. Calculer son SHA-256, annoncer versionName 0.5.0 et versionCode 7 uniquement si le dernier APK publié reste inférieur à 7. L'API de mise à jour et la page de téléchargement ne doivent pointer vers le candidat qu'après approbation. Le QR général continue de pointer vers `/download`.

## Retour arrière

- Avant réouverture des écritures : remettre le code, le WSGI et le venv précédents ; restaurer le snapshot validé dans un nouveau fichier, vérifier intégrité et permissions puis basculer le chemin des données. Reload contrôlé et recette minimale.
- Si de nouvelles transactions réelles ont été acceptées après bascule : ne pas restaurer aveuglément l'ancien snapshot. Suspendre les écritures, sauvegarder l'état courant, préserver les encaissements et mouvements nouveaux, puis préparer une réconciliation ou une correction avant remise en service.
- L'APK ne peut pas être rétrogradé normalement avec un versionCode inférieur. Préparer une version corrective avec le certificat permanent et un versionCode supérieur. Ne pas générer une nouvelle clé.
- Les anciennes installations signées debug ne peuvent pas être mises à jour par une clé release différente. Comparer les certificats des deux APK ; documenter la réinstallation si nécessaire.

## Certificats et Google

Renseigner dans Firebase `tunibiz-782f0` l'application `tn.tunibiz.tunibiz_mobile` et les SHA-1/SHA-256 du certificat release permanent affichés par la vérification locale. Ne jamais partager le keystore ni son mot de passe. Ajouter le client OAuth Android correspondant et le client Web utilisé par le serveur. URI de redirection Web : `https://ihebhaouech.pythonanywhere.com/auth/google/callback`.

Les valeurs Firebase publiques SDK peuvent être passées au build après validation. Aucun secret de compte de service ne doit être inclus dans l'APK. La configuration FCM et ses tests restent à développer : cette procédure ne les active pas.
