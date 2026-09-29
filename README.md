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

## Veille présidentielle : sources de fond

- `data/election-program-reviewed.json` contient la revue datée de chaque candidat, les documents de campagne et les sources de chaque rubrique. Les éditions antérieures, les projets collectifs, les orientations et les annonces personnelles sont distingués.
- Les synthèses vérifiées complètent les rubriques vides. Une synthèse déjà gérée par cette revue peut être corrigée ; une nouvelle proposition ajoutée séparément n'est pas écrasée.
- `scripts/election_background.py` contrôle jusqu'à deux sources par candidat actif et par collecte, avec rotation lorsque la fiche comporte plus de documents. Il surveille les pages HTML, les documents PDF et les liens vers de nouveaux programmes. Un premier accès établit une référence ; un échec ne remplace jamais la date du dernier accès réussi.
- Une modification de source est signalée dans la fiche, sans réécrire automatiquement le programme. Un changement de page ne prouve pas à lui seul une nouvelle proposition.
- Une recherche complémentaire sur 365 jours couvre 12 candidats par collecte, avec une rotation indépendante des partis et de leur présence médiatique. Les articles repérés restent des pistes à examiner, distinctes des propositions et controverses validées.
- La surveillance ne garantit pas l'exhaustivité : pages protégées, programmes en images, nouveaux sites et informations hors des sources suivies peuvent exiger une vérification supplémentaire. L'interface affiche l'état des documents suivis.
- Vérification : `python -m unittest discover -s scripts -p 'test_election_background.py'` et `node --check app.js`.
