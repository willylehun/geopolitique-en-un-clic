# Géopolitique en un Clic — PWA

Application mobile/web installable pour afficher une veille géopolitique et économique mondiale.

## Menus
- **Menu géographique** : International, Europe, Asie, Amérique du Nord, Amérique du Sud, Afrique, Océanie.
- **Menu temporel** : Jour, Semaine, Mois.
- **Historique** : l'application lit automatiquement les périodes disponibles via `bucket` dans `data/news.json`.

## Règle éditoriale
- Ne conserver que les informations **notées de 5/10 à 10/10**.
- Prioriser la géopolitique, l'économie, les conflits, l'énergie, la diplomatie, la sécurité et les sujets à fort impact.
- Résumé **très court**, style télégraphique.
- Toujours afficher les **sources entre parenthèses**.
- Regrouper les articles parlant du même événement en une seule entrée.

## Cadence de veille
- **Mise à jour quotidienne à 06h30 (heure de Paris)**.
- Chaque édition résume la période **de 06h30 la veille à 06h29 le jour même**.
- **Initialisation exceptionnelle** : backfill sur la **semaine précédente**, jour par jour + condensé hebdomadaire.
