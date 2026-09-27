# Android / Google Play

Architecture : Trusted Web Activity, pas WebView.

- Package : `com.willylehun.geopolitiqueenunclic`
- URL : `https://willylehun.github.io/geopolitique-en-un-clic/`
- compileSdk / targetSdk : 36
- minSdk : 23
- Android Browser Helper : 2.7.3
- Fallback : Custom Tabs, jamais WebView
- Permission : INTERNET uniquement
- HTTP clair : désactivé

## Signature
La clé privée reste hors du dépôt. Le build release lit :
`ANDROID_KEYSTORE_PATH`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`.

## Point restant pour Digital Asset Links
Android exige :
`https://willylehun.github.io/.well-known/assetlinks.json`

La Pages actuelle est une Project Page sous `/geopolitique-en-un-clic/`. Il faudra donc soit créer le dépôt utilisateur `willylehun/willylehun.github.io`, soit utiliser un domaine personnalisé. Le fichier de ce dépôt est prêt pour un futur domaine personnalisé.

Après activation de Play App Signing, ajouter aussi l'empreinte SHA-256 du certificat de signature Play au fichier assetlinks.
