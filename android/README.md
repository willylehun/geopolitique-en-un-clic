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

## Digital Asset Links

La racine GitHub Pages est maintenant configurée via le dépôt `willylehun/willylehun.github.io`.

Le fichier est publié à l'emplacement exigé par Android :

`https://willylehun.github.io/.well-known/assetlinks.json`

Les workflows Android vérifient automatiquement sa disponibilité, le package Android et l'empreinte de la clé d'upload.

Après activation de Play App Signing, ajouter aussi l'empreinte SHA-256 du certificat de signature Play au même fichier assetlinks.
