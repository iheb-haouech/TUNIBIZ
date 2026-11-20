# QR fidelite puis Facebook - pilote TUNIBIZ

Le QR imprime reste le lien `/join/<slug>`. Le commerce configure sa page Facebook depuis `/merchant-qr`, dans "Facebook apres le scan", ou depuis les validations QR dans la nouvelle version Android. Le lien exact de Facebook pour le pilote Makhzen Djerbi reste a renseigner par le proprietaire.

## Parcours

1. Un client non connecte se connecte a son compte TUNIBIZ puis reprend son scan. Une visite GET ou un simple apercu du lien ne cree aucun mouvement de points.
2. Le client confirme son passage. La verification email existante continue de s'appliquer.
3. Une confirmation indique soit les points de bienvenue effectivement credites, soit la demande d'achat en attente du commercant. Le bonus de bienvenue n'est jamais recree par un nouveau scan.
4. Si le commerce a configure une destination Facebook valide, la page s'ouvre apres trois secondes. Un bouton permet d'annuler cette ouverture ou de l'ouvrir manuellement. Le popup est affiche dans TUNIBIZ avant Facebook, pas dans Facebook.

Le lien de destination provient de la configuration du commercant, jamais d'un parametre fourni par le client. Les ecritures sont protegees par l'authentification commercant et le CSRF. Les URL non HTTPS, les faux sous-domaines, les ports et les informations utilisateur sont refuses. Effacer le lien desactive Facebook sans modifier le QR ni les regles de points.

## Validation effectuee le 20 novembre 2026

- `test_store_scan.py` : regression des points, de la validation commercant, des doublons et de l'isolation des commerces.
- `test_scan_facebook.py` : destination par commerce, refus des liens non autorises, CSRF, absence de points sur GET/compte anonyme/email non confirme, bonus unique et demandes rejouees.
- `test_commerce.py` : 15 controles existants passes.
- `test_scan_facebook_browser.py` : navigateur Edge sans interface, base jetable, page Facebook interceptee localement. Connexion puis reprise, popup avant redirection, etats bienvenue/en attente, annulation avec Echap, absence de destination et echec de scan testes ; aucune erreur JavaScript observee.
- Flutter : 32 tests passes, dont ouverture differee, absence de double ouverture, annulation et destination invalide. Les tests de restauration de compte continuent de passer.
- Affiche A4 : les deux QR se decodent sur le rendu final 300 dpi et sur l'apercu, y compris le logo dans le QR central. Le QR central identifie le commerce actif `cd8f57567e0a88135bf84f51` (Makhzen Djerbi) ; celui de l'application pointe sur `/download`.

Ces controles utilisent des comptes de recette isoles, sans creer de points en production. L'ouverture dans l'application Facebook sur un telephone physique et la compilation Android du nouveau pont natif restent a valider. L'APK 0.5.2 deja publie n'est pas remplace par cette branche.

## Activation restante

Le serveur en ligne n'a pas ete modifie dans cette etape. Sauvegarder la base puis deployer cette branche sur PythonAnywhere avec la configuration privee existante et effectuer un Reload. Le seul ajout de schema est la table `store_qr_settings`, creee a l'import.

Ensuite, se connecter au compte du commerce sur `/merchant-qr`, saisir le lien Facebook exact et l'enregistrer. Tester avec un compte client confirme : bonus de bienvenue une seule fois, scan suivant en attente, validation par le bon commercant et ouverture de la bonne page Facebook.

Pour le scanner integre a Android, compiler un nouvel APK signe avec le certificat permanent et un versionCode superieur a celui de toute livraison deja publiee. La partie web du parcours peut etre deployee independamment, avec le meme QR imprime.
