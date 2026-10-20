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

**C'est la seule chose qui peut encore invalider les décisions prises.** Les pondérations
45/25/15/15 et λ = 0,40 sont des hypothèses de design, pas des mesures.

- [ ] Extraire Wikidata + pageviews sur un échantillon ciblé, puis sur quelques milliers
      d'artistes.
- [ ] Calculer les scores et vérifier le classement contre les cas de référence listés
      dans [`03-rarete-scoring.md`](03-rarete-scoring.md) : Portnoy ≥ LaBrie,
      Manson > John 5 tous deux en haut palier, les 9 de Slipknot bien répartis,
      Dave Mustaine en haut palier, aucun artiste absurde en Mythique.
- [ ] **Mesurer la couverture réelle des champs** — quelle proportion d'artistes a
      effectivement un `P1303`, un `P136`, des dates d'appartenance. C'est ça qui dira
      si les sept couches de composition sont réellement alimentables.
- [ ] Ajuster les pondérations et λ, puis les figer.

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
