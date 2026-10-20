
# Rareté et scoring

## Principes

1. **Toujours en échelle logarithmique.** La popularité suit une loi de puissance
   brutale : sans `log10`, on n'obtient que deux classes.
2. **Multi-signaux.** Les pageviews seuls sont biaisés vers l'actualité immédiate et le
   monde anglophone. Il faut mélanger du « buzz » et du « patrimoine ».
3. **Mesurer une position, pas un volume.** Les vues se comparent à l'intérieur d'une
   communauté linguistique, jamais en valeur absolue d'une édition à l'autre.
4. **Rareté ≠ puissance.** La rareté doit rester de la *rareté*. Si les cartes rares sont
   mécaniquement supérieures, le jeu devient pay-to-grind et le marché se déséquilibre.
5. **Paliers par rang centile, jamais par seuil absolu.** Sinon l'héritage de groupe
   gonfle les hauts paliers de façon incontrôlable.

## Score personnel

```
score_perso = 0,40 · z(log part_pageviews)
            + 0,20 · z(log sitelinks)
            + 0,15 · max(0, z(entropie linguistique))     ← bonus seul, jamais un malus
            + 0,10 · z(log richesse Wikidata)
            + 0,15 · z(log volume discographique)
```

| Composante | Détail |
|---|---|
| **Part de pageviews** (40 %) | Position de l'artiste **au sein de chaque communauté linguistique**, et non somme brute des vues. Médiane mensuelle sur 24 mois : elle écrase les pics (décès, sortie d'album) que la moyenne laisserait passer. Voir la formule ci-dessous. |
| **Sitelinks** (20 %) | Nombre de versions linguistiques de la page. Proxy de notoriété *durable* et interculturelle. |
| **Entropie linguistique** (15 %) | Dispersion des vues entre éditions. Un artiste lu dans quarante langues est plus universel qu'un artiste lu dans une seule, à total égal. |
| **Richesse Wikidata** (10 %) | Nombre de déclarations, identifiants externes, récompenses `P166`. |
| **Discographie** (15 %) | Volume de releases et recordings MusicBrainz. |

> Les pondérations sont des **hypothèses de design**, pas des mesures. Elles doivent
> être validées sur données réelles avant d'être figées.

### Pourquoi une part et non une somme

La validation a mesuré le problème : en sommant les vues brutes, l'édition anglophone
pèse un ordre de grandeur de plus que toutes les autres, donc **la somme *est* le score
anglophone**. Aya Nakamura, écrasante sur `fr.wikipedia`, ressortait 31ᵉ sur 38.

On mesure donc la position de l'artiste dans chaque communauté linguistique, pondérée
par la taille de cette communauté :

```
part_pageviews = Σ_w  √(V_w) · ( vues_artiste,w / médiane_musiciens_w )
```

- `V_w` est le trafic musical total de l'édition `w`. Sa **racine carrée** amortit la
  domination de l'anglais sans nier qu'il couvre un public bien plus large — sans ce
  facteur, un artiste connu uniquement en catalan dépasserait une star mondiale.
- `médiane_musiciens_w` se calcule sur la population de musiciens de chaque édition,
  obtenue par la même jointure Wikidata × dumps que le reste du pipeline.

### Les deux garde-fous contre la pénalisation des marchés uniques

L'entropie récompense l'universalité, mais elle ne doit **pas** punir la domination
locale. Johnny Hallyday est colossal en France et quasi inconnu ailleurs ; il doit rester
Mythique. Même raisonnement pour les grands noms de l'enka japonaise ou du playback
de Bollywood.

**1. L'entropie est un bonus, jamais un malus.** On la clampe à `max(0, z)` :
l'étendue linguistique fait monter, la concentration ne fait pas descendre. Gojira,
diffusé dans huit communautés, touche son bonus ; Johnny Hallyday n'en touche pas mais
ne perd rien.

**2. Plancher de domination de marché.** Un artiste classé dans le top 1 % des musiciens
sur **n'importe quelle** édition se voit garantir un palier minimum, indépendamment de sa
diffusion mondiale. Même mécanique que le plancher de prestige des membres de groupes
cultes : qui écrase son marché est rare, point.

> Le cas inverse ne pose pas de problème. Un artiste plus connu à l'étranger que chez lui
> — Gojira en est l'exemple type — n'est jamais pénalisé, parce que la normalisation est
> **par édition et non par nationalité** : la formule ne demande jamais d'où vient
> l'artiste. Sa position modeste sur `fr` contribue simplement moins, elle ne retranche
> rien.

### Test de recette

Après implémentation, rejouer la validation et vérifier **les deux sens à la fois** :
Aya Nakamura doit remonter nettement, **sans que** Miles Davis ni Nina Simone ne
dégringolent. Si un seul des deux bouge, la pondération `√(V_w)` est mal calibrée.

### Sur les compteurs d'écoutes

**Écartés, après examen.** L'idée d'ajouter un volume d'écoutes pour contrer le biais
anglophone est séduisante mais contre-productive :

- **ListenBrainz**, notre seule source d'écoutes en CC0, repose sur une base
  d'utilisateurs réduite et très typée — public occidental, technophile, massivement
  rock, metal et électronique. Elle amplifierait le biais au lieu de le corriger.
- Les sources qui corrigeraient réellement (Spotify, YouTube, Deezer) sont précisément
  celles écartées pour raisons de conditions d'utilisation — voir
  [`02-donnees.md`](02-donnees.md).
- Un compteur d'écoutes introduit un **biais de récence** massif : le streaming favorise
  les artistes actifs après 2010, et effondrerait Miles Davis ou Nina Simone face à des
  contemporains. Notre score mélange délibérément buzz et patrimoine ; les écoutes sont
  du buzz pur.

La normalisation par édition corrige le biais à la source, sans source nouvelle, sans
risque juridique et à coût nul puisqu'elle se calcule sur les dumps déjà nécessaires.

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
