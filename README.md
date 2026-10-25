# Fantasy Music — jeu de cartes à collectionner sur navigateur

Jeu de collection navigateur autour d'artistes musicaux réels. Une carte par personne
(jamais par groupe), obtenue en ouvrant des boosters, échangeable sur un marché en
monnaie virtuelle non convertible.

Contraintes fondatrices du projet :

- **Coût minimal** — ressources gratuites et licences libres partout où c'est possible.
- **Cadre légal strict** — aucune donnée ni visuel dont l'usage commercial est douteux.
- **Zéro argent réel en entrée comme en sortie** — pas de booster payant, pas de cash-out,
  pas de NFT. C'est ce qui maintient le jeu hors du champ des jeux d'argent.

## Organisation

| Document | Contenu |
|---|---|
| [`docs/01-cadre-juridique.md`](docs/01-cadre-juridique.md) | Droit à l'image, droit d'auteur, RGPD, loot boxes |
| [`docs/02-donnees.md`](docs/02-donnees.md) | Sources retenues et écartées, pipeline d'ingestion |
| [`docs/03-rarete-scoring.md`](docs/03-rarete-scoring.md) | Score composite, héritage de groupe, éligibilité, cliquet |
| [`docs/04-distribution.md`](docs/04-distribution.md) | Boosters, taux de tirage, pity timer, volumétrie des paliers |
| [`docs/05-direction-artistique.md`](docs/05-direction-artistique.md) | Trois styles, couches de composition, mapping des genres |
| [`docs/06-reste-a-faire.md`](docs/06-reste-a-faire.md) | Ce qui est tranché, ce qui ne l'est pas |
| [`docs/07-validation-resultats.md`](docs/07-validation-resultats.md) | Scoring sur données réelles |
| [`docs/08-serie-1.md`](docs/08-serie-1.md) | Taille, mélange, algo de draft |
| [`docs/09-schema-donnees.md`](docs/09-schema-donnees.md) | Catalogue, cliquet, appendice joueur |
| [`docs/10-pipeline.md`](docs/10-pipeline.md) | Runbook pageviews → catalogue → WebP |
| [`docs/11-marche.md`](docs/11-marche.md) | Marché à prix fixe, taxe 10 % |

`references/` contient les quatre illustrations de direction artistique.
`prototypes/` contient les maquettes HTML autonomes (ouvrables via serveur local).
Pages légales (brouillon) : [`prototypes/legal/`](prototypes/legal/).

## Découpage en briques

1. **Création et distribution des cartes** — données, rareté, boosters, visuel. *En cours.*
2. **Économie** — monnaie, poussière, marché, puits d'inflation, anti-bot. *Non démarrée.*
3. **Boucle de jeu** — que fait-on des cartes au-delà de la collection. *Non démarrée.*

## État de la brique 1

Mécaniques et Série 1 (2 000, mélange 80/400/900/600) sont arrêtées. Restent les
planchers d'équilibre, quelques correctifs de pipeline, et la production des assets.
Voir [`docs/06-reste-a-faire.md`](docs/06-reste-a-faire.md).
