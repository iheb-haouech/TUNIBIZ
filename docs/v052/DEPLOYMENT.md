# TUNIBIZ V0.5.2 - procédure de bascule

État : livraison candidate. Le site en ligne n'a pas été modifié. La connexion PythonAnywhere a été refusée pendant cette session.

## Préconditions

- Connexion au compte PythonAnywhere du propriétaire.
- Code V0.5.2 de la branche `feature/v0.5.2-ux-commercial`.
- Conservation du secret Flask, des configurations OAuth/Gmail/Firebase, du certificat Android et des données existantes.
- Aucun service SMS n'est déclaré opérationnel. Les téléphones restent explicitement non vérifiés.

## Déploiement

1. Relever le SHA et les répertoires du code et du venv actuellement utilisés, ainsi que le fichier WSGI. Ne pas écraser les fichiers privés de configuration.
2. Arrêter les écritures pendant la migration et effectuer une sauvegarde SQLite cohérente via `mvp/backup_db.py`, hors du répertoire public. Valider `integrity_check` et `foreign_key_check`.
3. Tester l'import du nouveau code sur une copie privée de la base de production. Conserver les comptes et les relations existants. Vérifier le nombre de lignes avant/après.
4. Installer le code dans un nouveau répertoire et utiliser le venv existant seulement s'il satisfait `requirements.lock`. Les nouvelles fonctionnalités n'introduisent pas de dépendance Python supplémentaire.
5. Importer `app` une fois dans le contexte de maintenance pour appliquer les migrations additives. Les promotions historiques de campagnes et de Nearby sont reliées à des promotions canoniques, sans supprimer les anciennes tables.
6. Basculer le WSGI vers le nouveau répertoire et effectuer un Reload unique. Vérifier HTTPS, les trois connexions, la recherche téléphone, 20 points sans montant, les codes propres au commerce, les coupons et le refus d'accès inter-commerces.
7. Réouvrir les écritures après succès des contrôles critiques. Les anciennes vitrines ne sont pas automatiquement publiées : renseigner la photo principale et le contact, puis publier explicitement.
8. Tester l'APK V0.5.2 sur un appareil Android réel déjà équipé de la V0.5.1, sans désinstaller ni effacer les données. Vérifier Google, la restauration de session, les photos, les permissions et les notifications.
9. Publier l'APK et ses métadonnées seulement après ces contrôles. La page /download et l'API de mise à jour n'ont pas été modifiées pendant cette session.

## Notifications

Les mouvements de points, paliers d'avantages et coupons alimentent une boîte de notifications et une file FCM. Le worker `python mvp/fcm_dispatch.py --send` utilise l'identité serveur existante. Son exécution automatique et l'envoi FCM réel doivent être validés sur le plan PythonAnywhere en vigueur. Sans `--send`, aucun appel FCM n'est effectué. Aucun identifiant privé n'est inclus dans l'APK.

## Retour arrière

Avant réouverture des écritures, remettre le WSGI et le code précédents. La migration ajoute des tables/colonnes et conserve les anciennes données. Restaurer une sauvegarde uniquement si aucune transaction nouvelle n'a été acceptée. Si des écritures ont eu lieu, sauvegarder l'état courant et réconcilier les données au lieu d'écraser les nouvelles transactions. Android nécessite un nouveau build avec un versionCode supérieur pour une correction ; une rétrogradation n'est pas une procédure normale de retour arrière.
