# Préparation Google Play — Géopolitique en un Clic

Ce dossier prépare la publication Google Play sans nécessiter encore de compte Play Console.

## État technique
- Application Android : Trusted Web Activity (TWA), sans WebView.
- Package : `com.willylehun.geopolitiqueenunclic`.
- Cible : Android 16 / API 36.
- Permission Android : INTERNET uniquement.
- Trafic HTTP clair : interdit.
- Signature release : secrets GitHub uniquement, aucune clé privée dans le dépôt.
- Digital Asset Links : vérifiés par le workflow Android.

## À faire lorsque le compte développeur sera disponible
1. Créer l'application dans Play Console avec le même package.
2. Activer Play App Signing.
3. Ajouter l'empreinte SHA-256 du certificat de signature Play à `/.well-known/assetlinks.json`.
4. Importer l'AAB produit par le workflow « Construire Android Play Store ».
5. Reprendre et confirmer les déclarations de `data-safety-fr.md` selon la version réellement publiée.
6. Publier la politique de confidentialité à une URL publique stable et saisir cette URL dans Play Console.
7. Compléter la classification du contenu et déclarer l'application comme application d'actualités si Play Console le demande.
8. Effectuer les tests Play requis avant production.

Ne jamais placer de mot de passe, clé de signature ou jeton Play Console dans ce dossier.
