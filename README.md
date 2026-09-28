# Géopolitique en un Clic — PWA

Application mobile/web installable pour afficher une veille géopolitique et économique mondiale.

## Menus
- **Menu géographique** : International, Europe, Asie, Amérique du Nord, Amérique du Sud, Afrique, Océanie.
- **Menu temporel** : Jour, Semaine, Mois.
- **Historique** : l'application lit automatiquement les périodes disponibles via `bucket` dans `data/news.json`.

## Règle éditoriale
- Conserver uniquement des informations **utiles à la compréhension géopolitique**.
- Écarter sport, people, divertissement, loisirs, faits divers locaux et contenus promotionnels lorsqu'ils n'ont pas de conséquence politique, institutionnelle, économique ou internationale réelle.
- Un résumé doit apprendre au moins un **fait, une décision, une évolution mesurable ou une conséquence** ; les titres vagues, éditoriaux sans information concrète et textes SEO sont rejetés.
- Une actualité automatique du jour n'est publiée que si le moteur dispose d'un **résumé enrichi à partir du contenu/description de l'article** ; un simple titre n'est pas suffisant.
- Lorsqu'une personne publique est identifiée avec certitude, l'affichage précise **sa fonction + son nom + (son pays)**, par exemple « le président Donald Trump (États-Unis) » ou « le trésorier fédéral Jim Chalmers (Australie) ».
- Tous les résumés visibles sont en français naturel ; une source étrangère reste utilisable et doit être traduite/synthétisée.
- **International** est réservé aux événements d'importance géopolitique >= 7/10.
- Toujours afficher les sources et regrouper les articles parlant du même événement en une seule entrée.
- Jour, Semaine et Mois sont triés du **plus récent au plus ancien**.

## Cadence de veille
- Journée éditoriale : **00:00 → 23:59, Europe/Paris**.
- Veille mondiale : environ **6 collectes réelles par heure**, avec réveils GitHub redondants et garde-fou anti-empilement.
- Veille Présidentielle française 2027 : environ **une collecte réelle par heure**, séparée de la veille mondiale.
- Les **195 pays** restent en permanence dans la rotation ; la priorité varie selon l'heure mais aucun pays n'est exclu.
