# Sécurité des données Google Play — préparation

Ce document est un brouillon de travail. Les réponses doivent être revérifiées dans Play Console contre la version exacte de l'application publiée.

## État observé dans le projet Android
- Permission : INTERNET uniquement.
- Aucun compte utilisateur requis.
- Pas de permission localisation.
- Pas de permission contacts.
- Pas de permission SMS/téléphone.
- Pas de permission caméra/microphone.
- Pas de permission fichiers/médias.
- Pas de SDK publicitaire déclaré dans le module Android.
- TWA vers le site officiel, sans WebView intégré.

## Avant de remplir « Sécurité des données »
Vérifier à nouveau :
- scripts Web et éventuels services d'analytique ;
- cookies et stockage navigateur ;
- journaux techniques de l'hébergeur ;
- tout SDK ajouté depuis ce contrôle ;
- formulaires, authentification ou données envoyées par l'utilisateur ;
- publicité ou mesure d'audience ajoutée ultérieurement.

Ne jamais déclarer « aucune donnée collectée » uniquement sur la base des permissions Android : la déclaration Play doit tenir compte du comportement du site chargé par la TWA et des SDK/services réellement utilisés.
