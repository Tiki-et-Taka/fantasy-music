
# Rareté et scoring

## Principes

1. **Toujours en échelle logarithmique.** La popularité suit une loi de puissance
   brutale : sans `log10`, on n'obtient que deux classes.
2. **Multi-signaux.** Les pageviews seuls sont biaisés vers l'actualité immédiate et le
   monde anglophone. Il faut mélanger du « buzz » et du « patrimoine ».
3. **Rareté ≠ puissance.** La rareté doit rester de la *rareté*. Si les cartes rares sont
   mécaniquement supérieures, le jeu devient pay-to-grind et le marché se déséquilibre.
4. **Paliers par rang centile, jamais par seuil absolu.** Sinon l'héritage de groupe
   gonfle les hauts paliers de façon incontrôlable.

## Score personnel

```
score_perso = 0,45 · z(log pageviews)
            + 0,25 · z(log sitelinks)
            + 0,15 · z(log richesse Wikidata)
            + 0,15 · z(log volume discographique)
```

| Composante | Détail |
|---|---|
| **Pageviews** (45 %) | Somme de **toutes** les langues, **médiane** mensuelle sur 24 mois. La médiane écrase les pics (décès, sortie d'album), contrairement à la moyenne. |
| **Sitelinks** (25 %) | Nombre de versions linguistiques de la page. Excellent proxy de notoriété *durable* et interculturelle. |
| **Richesse Wikidata** (15 %) | Nombre de déclarations, identifiants externes, récompenses `P166`. |
| **Discographie** (15 %) | Volume de releases et recordings MusicBrainz. |

> Les pondérations sont des **hypothèses de design**, pas des mesures. Elles doivent
> être validées sur données réelles avant d'être figées.

## Héritage de notoriété du groupe

**Pas de poids de rôle : chaque instrument vaut autant.**

C'était le point clé du débat. Si Marilyn Manson est bien plus rare que John 5, ce n'est
pas parce qu'il chante — c'est parce que ses propres pageviews et sitelinks l'écrasent.
L'écart vient des **données**, pas d'un coefficient. Un poids de rôle produirait
exactement l'effet indésirable : placer James LaBrie au-dessus de Mike Portnoy alors que
les données disent le contraire.

```
score_final = score_perso + λ · contribution · max(0, score_groupe − score_perso)

avec λ = 0,40
```

Le terme `max(0, écart)` fait l'essentiel du travail :

- un membre dont le score égale déjà celui du groupe ne gagne **rien** ;
- les autres sont remontés proportionnellement à leur retard.

> ⚠ **Correction apportée après validation sur données réelles.** Cette formule ne
> préserve l'ordre interne au groupe que si la contribution est **identique** pour tous
> les membres. Dès qu'elle varie, un membre moins connu mais mieux doté en contribution
> peut dépasser un membre plus connu — observé chez Slipknot, voir
> [`07-validation-resultats.md`](07-validation-resultats.md).
>
> **Parade obligatoire :** après calcul, trier les membres d'un groupe par `score_perso`
> décroissant et contraindre `score_final` à être non croissant dans cet ordre. La
> préservation devient alors structurelle au lieu d'être espérée.

### Poids de contribution

```
contribution = max( min(1, années_présence / 5),
                    albums_studio_participés / albums_studio_total )
```

- La première branche sature à cinq ans, **indépendamment de l'âge du groupe**. Le ratio
  `années / durée_totale_du_groupe` serait injuste : un an chez les Rolling Stones
  donnerait 0,016.
- La seconde branche est souvent la plus juste en musique : avoir joué sur trois albums
  sur dix compte plus que du temps de calendrier. Elle capture le membre resté six mois
  mais présent sur l'album culte.
- Deux semaines sans une seule session en studio donnent zéro sur les deux branches.

### Multi-groupes

```
score_groupe = meilleur_groupe + 0,25 · second_meilleur_groupe
```

John 5 a joué avec Marilyn Manson **et** Rob Zombie : c'est mérité.

### Garde-fous

- **Plafond d'héritage :** la promotion par héritage ne peut pas dépasser **deux
  paliers**. Sinon un musicien de session de Slipknot passerait de Commune à Légendaire.
- **Plancher de prestige :** un membre historique d'un groupe du top mondial ne descend
  pas sous Rare, pour garantir qu'un groupe culte soit toujours représenté par des cartes
  désirables.

## Éligibilité : qui obtient une carte

**Aucun critère de durée.** Le filtre d'ancienneté initialement envisagé était redondant
et nuisible : le membre resté deux semaines est déjà neutralisé par le poids de
contribution dans l'héritage, et le filtre ne faisait qu'exclure des cartes légitimes.

Dave Mustaine n'a tenu qu'un peu plus d'un an chez Metallica, viré avant le premier
album, et il est mythique — mais sa rareté vient de Megadeth, donc de son score
personnel. Jason Everman n'a fait que quelques mois chez Nirvana puis Soundgarden : sa
notoriété propre fait le travail. À l'inverse Ron McGovney, premier bassiste de
Metallica, est juste assez notable pour exister et son faible score le laisse à sa place.

**Le « côté mythique » est déjà dans les données.** Un membre éphémère dont on parle
encore trente ans après a des pageviews et des sitelinks qui le disent.

### Critères retenus

1. Membre **officiel** — les qualificatifs de rôle Wikidata et les attributs
   d'appartenance MusicBrainz permettent d'écarter les musiciens de tournée et de session.
2. Page Wikipédia dans **au moins 2 langues**.
3. **Plafond de sécurité à 15 membres** par groupe, classés par score, uniquement pour
   les cas pathologiques (King Crimson compte une vingtaine de membres historiques,
   Menudo plusieurs dizaines). Ce plafond laisse passer sans effort Slipknot (9),
   le Wu-Tang Clan (10) et Arcade Fire.

Les membres virés ou éphémères constituent un sous-genre de collection à exploiter :
un tag **« Éphémère »** ou une mini-série « Line-ups » (Mustaine, Pete Best,
Chad Channing, Stuart Sutcliffe) donne de la valeur à des cartes que le scoring
classerait bas.

## Cliquet de rareté

```
rareté_affichée = max(rareté_initiale, rareté_recalculée)
```

Une carte peut **monter** de palier, jamais descendre. Un artiste peu connu qui explose
doit voir sa carte gagner en rareté.

### L'effet de bord est une mécanique majeure

Les joueurs vont stocker des communes d'artistes émergents en pariant sur la promotion.
Cela crée une fantasy de **dénicheur de talents** et donne enfin une raison de
s'intéresser aux petits noms plutôt qu'aux seules légendes.

### Précautions

| Risque | Parade |
|---|---|
| Promotion sur un pic transitoire (décès d'un artiste) | Exiger un signal **soutenu** : deux trimestres consécutifs au-dessus du seuil, sur la médiane 24 mois |
| Bruit permanent, joueurs désorientés | Ne re-noter qu'aux **frontières de série**, avec une fenêtre annoncée |
| Dérive des effectifs de paliers sur dix ans | Sortir la carte promue du pool commun des boosters futurs ; le classement par centile corrige automatiquement |
| Bousculer l'économie des cartes déjà possédées | Variante : la carte garde son palier d'origine mais gagne un traitement **« Ascension »** (chevron), et c'est la nouvelle série qui l'imprime au palier supérieur |

## Cas de référence à vérifier lors de la validation

| Attendu | Pourquoi c'est un test |
|---|---|
| Mike Portnoy ≥ James LaBrie | Vérifie qu'aucun bonus de rôle ne s'est glissé dans le calcul |
| Marilyn Manson > John 5, les deux en haut palier | Vérifie que l'héritage remonte sans inverser |
| Les 9 de Slipknot tous présents et bien répartis | Vérifie le filtre d'éligibilité |
| Aucun artiste absurde en Mythique | Vérifie les pondérations du score |
| Dave Mustaine en haut palier | Vérifie l'absence de filtre d'ancienneté |
