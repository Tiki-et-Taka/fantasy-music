# Brique 1 — reste à faire

## Tranché

- Sources de données retenues et écartées.
- Score composite 45 / 25 / 15 / 15.
- Héritage de groupe sans poids de rôle, λ = 0,40, contribution à double branche.
- Critères d'éligibilité, sans filtre d'ancienneté, plafond de sécurité à 15 membres.
- Cliquet de rareté et ses garde-fous.
- Structure du booster à slots, taux de tirage, pity timer.
- Volumétrie des six paliers.
- Cadre juridique : aucune photo, aucun visage identifiable, portraits en opt-in
  uniquement, procédure de retrait, pas d'argent réel en entrée ni en sortie.
- Trois styles d'illustration et leur escalade par rareté.
- Sept couches de composition.
- Sceau de groupe génératif.
- Vingt familles de genres, palettes et ordre de priorité.

## Chemin critique — validation sur données réelles

- [x] Extraire Wikidata + pageviews sur un échantillon ciblé de 38 artistes et
      7 groupes — `tools/validate_scoring.py`.
- [x] Vérifier le classement contre les cas de référence : **8/8 validés**.
- [x] Mesurer la couverture des champs.
- [ ] Corriger les trois points remontés par la validation (ci-dessous).
- [ ] Rejouer, puis passer à l'extraction large pour caler les centiles et figer les
      pondérations 45/25/15/15 et λ = 0,40, qui restent des hypothèses.

Résultats détaillés dans [`07-validation-resultats.md`](07-validation-resultats.md).

### Corrections issues de la validation

- [ ] **Monotonie intra-groupe.** L'héritage peut inverser l'ordre interne quand la
      contribution varie d'un membre à l'autre. Contraindre `score_final` à être non
      croissant dans l'ordre de `score_perso` au sein de chaque groupe.
- [ ] **Dates d'appartenance.** Couverture Wikidata mesurée à 47 % seulement, sur un
      échantillon pourtant très célèbre. Brancher MusicBrainz en source primaire, puis
      remesurer.
- [ ] **Pageviews par dumps.** L'API REST est limitée à ~100 requêtes consécutives pour
      un client anonyme ; les 100 000 requêtes d'une Série 1 sont hors de portée.
      Passer aux dumps mensuels.

## Décisions ouvertes

- [ ] **Taille de la Série 1.** 2 000 est une hypothèse de travail.
- [ ] **Quotas de curation** par genre, époque et pays. Prendre le top 2 000 par score
      produit mécaniquement un set à 80 % anglo-saxon : les pageviews y mènent tout
      droit. Arbitrage éditorial, pas technique.
- [ ] Découpage en extensions et rythme de sortie.

## À produire

Par ordre d'urgence :

- [ ] **Planche de validation sérigraphie** — six illustrations, instruments et époques
      différents, pour vérifier que le style tient la variété *avant* de commander quoi
      que ce soit.
- [ ] **Brief illustrateur détaillé** — les 8 familles d'instruments et leurs poses, les
      5 tranches de costume, les 5 décors. Aujourd'hui ce n'est qu'une intention.
      Inclure la ligne rouge de `01-cadre-juridique.md`.
- [ ] **Table d'override des 200 genres les plus fréquents.** Quelques heures de travail
      manuel qui portent l'essentiel de la qualité perçue.
- [ ] **Schéma de données** — carte, série, appartenance aux groupes, et surtout
      l'historique de rareté qu'exige le cliquet.
- [ ] **Pipeline technique** — requêtes SPARQL, ingestion pageviews, job mensuel sur
      GitHub Actions, pré-rendu des visuels.
- [ ] **Pages légales** — attribution Wikidata et MusicBrainz, disclaimer de
      non-affiliation, procédure de retrait, politique RGPD, page publique de
      transparence des taux de tirage.

## Hors brique 1

- Brique 2 — économie : monnaie, poussière, marché, taxe de transaction, anti-bot.
- Brique 3 — boucle de jeu : que fait-on des cartes au-delà de la collection.
