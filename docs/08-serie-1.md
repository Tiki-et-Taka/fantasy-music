# Série 1 — construction du catalogue

Tranché le 20 octobre 2026.

## Taille

**2 000 artistes.** Une carte par personne, jamais par groupe.

À 5 cartes par jour, c'est un peu plus d'un an de collection pour un joueur
uniquement gratuit. Les extensions suivantes ne vident pas un reliquat de no-names :
elles piochent dans la réserve d'icônes volontairement non consommée ici.

## Mélange de notoriété

Les 2 000 sièges se répartissent ainsi, **sur le rang dans tout le vivier éligible**,
pas dans la série :

| Bande | Sièges | Rang dans le vivier | Rôle |
|---|---:|---|---|
| Icônes | 80 | top ~3 % | Les visages de la boîte |
| Connus | 400 | 3–15 % | « Ah oui, celui-là » |
| Scène | 900 | 15–50 % | Cœur de la collection |
| Deep cuts | 600 | 50–80 % | Objet de chasse, synergie de groupe |

Le dernier quintile du vivier (80–100 %) est **exclu** : pages trop pauvres, pas de fun.

Les 80 icônes de la Série 1 **sont** le plafond de pantheon. Le vivier en contient
beaucoup plus (~400). Les autres restent en réserve pour la Série 2 et les extensions
thématiques. On n'écrème pas le haut du classement au premier soir.

## Comment on choisit, exactement

1. **Vivier.** Tous les éligibles (membre officiel, page dans ≥ 2 langues, plafond 15
   membres par groupe). Score calculé avec la formule de
   [`03-rarete-scoring.md`](03-rarete-scoring.md).
2. **Trois étiquettes** par artiste, dérivées des données : genre canonique, région
   (`P27` mappé vers 10 régions), époque (début de carrière → 4 tranches).
3. **Draft par bande, pas par sommet.** Pour chaque case encore déficitaire
   (genre / région / époque × bande de notoriété), on assied le mieux classé *de cette
   bande* qui porte l'étiquette. Un artiste n'occupe qu'une chaise, mais tamponne
   toutes les étiquettes qu'il honore.
4. **Filets éditoriaux.** Liste verte d'une cinquantaine d'intouchables (au cas où
   les données les rateraient). Liste rouge courte : veto, pas ranking.
5. **Rareté dans la série.** Une fois les 2 000 choisis, les paliers commune → diamant
   se calent par **centile dans ces 2 000**, pas dans le vivier mondial.

Si une case est impossible à remplir (pas assez d'éligibles), on baisse le plancher et
on trace l'écart. On ne gonfle pas avec des fiches vides.

## Planchers d'équilibre

Tranchés le 20 octobre 2026. Ce sont des **minima**, pas des parts. Un artiste n'occupe
qu'une chaise mais décrémente les trois axes (genre, région, époque). Les sièges
non réservés (~600 en genre, ~520 en région, ~450 en époque) se remplissent tout seuls
par la draft.

Chaque plancher est **tranché comme le set** : 4 % icônes, 20 % connus, 45 % scène,
30 % deep cuts, reste à la scène. On ne remplit donc pas « 180 rock » avec 180 stars
du rock.

Si une case est impossible (pas assez d'éligibles), on baisse le plancher et on note
l'écart. Pas de fiches fantômes.

### Genre — 1 385 sièges plancher

Les 17 familles de [`05-direction-artistique.md`](05-direction-artistique.md).
Gospel, classique et expérimental sont hors jeu : leurs 95 sièges ont été
réinjectés dans les familles qui tiennent en compétition de groupes.

| Famille | Plancher | Icônes | Connus | Scène | Deep cuts |
|---|---:|---:|---:|---:|---:|
| Rock | 200 | 8 | 40 | 90 | 62 |
| Pop | 155 | 6 | 31 | 70 | 48 |
| Métal | 130 | 5 | 26 | 59 | 40 |
| Hip-hop | 130 | 5 | 26 | 59 | 40 |
| Électronique | 110 | 4 | 22 | 50 | 34 |
| Jazz | 85 | 3 | 17 | 38 | 27 |
| R&B & soul | 75 | 3 | 15 | 34 | 23 |
| Chanson & variété | 75 | 3 | 15 | 34 | 23 |
| Punk & hardcore | 65 | 3 | 13 | 29 | 20 |
| Folk | 55 | 2 | 11 | 25 | 17 |
| Funk & disco | 55 | 2 | 11 | 25 | 17 |
| Latin | 50 | 2 | 10 | 22 | 16 |
| Afro | 50 | 2 | 10 | 22 | 16 |
| Country | 40 | 2 | 8 | 18 | 12 |
| Reggae & dub | 40 | 2 | 8 | 18 | 12 |
| Blues | 35 | 1 | 7 | 16 | 11 |
| Musiques du monde | 35 | 1 | 7 | 16 | 11 |
| **Total plancher** | **1 385** | **54** | **277** | **625** | **429** |
| Sièges libres | 615 | 26 | 123 | 275 | 171 |

Les 26 icônes libres restent sous le plafond global de 80.

### Région — 1 480 sièges plancher

Source : première nationalité `P27`, plus une courte table d'overrides (double
nationaux, Québec). Un pays n'appartient qu'à **une** région — le Maghreb n'est pas
aussi de l'Afrique, le Sénégal n'est pas aussi « francophone Europe ».

| Région | Plancher | Qui y tombe |
|---|---:|---|
| Monde anglophone | 500 | US, GB, IE, AU, NZ, CA (hors override QC) |
| Europe hors FR / anglophone | 220 | DE, IT, ES, PT, NL, SE, PL, CH, GR, Balkans, Baltiques… |
| Europe francophone | 180 | FR, BE, LU, MC + override Québec |
| Amérique latine | 120 | MX, BR, AR, CO, CL, PE, CU… |
| Afrique subsaharienne | 100 | NG, ZA, SN, CI, CD, GH, ML… |
| Asie de l'Est | 100 | JP, KR, CN, TW, HK |
| Maghreb & Moyen-Orient | 80 | MA, DZ, TN, EG, TR, IR, LB… |
| Europe de l'Est / ex-URSS | 80 | RU, UA, BY, KZ, GE, AM… |
| Asie du Sud & Sud-Est | 60 | IN, ID, TH, VN, PH, PK… |
| Autre | 40 | filet (IS, etc.) |
| **Total plancher** | **1 480** | |
| Sièges libres | 520 | |

L'anglophone a le plus gros plancher, c'est honnête. Il n'aura pas 80 % du set : les
sièges libres + les autres planchers le plafonnent de fait vers ~40–50 %.
L'Europe francophone à 180 (9 %) assume un jeu qui naît en français, sans en faire
un catalogue hexagonal.

### Époque — 1 550 sièges plancher

Source des **planchers** : début de carrière (`P2031`, sinon `P569` + 18 ans).
Source **affichée sur la carte et le costume** : période emblématique — décennie
où l'artiste a sorti le plus d'albums studio après 16 ans
(`tools/fetch_peak_era.py`). Un enfant star (Jackson 5 en 1964) n'est plus
habillé en sixties : Thriller / Bad le mettent en 1970–89.

| Tranche | Plancher | Icônes | Connus | Scène | Deep cuts |
|---|---:|---:|---:|---:|---:|
| ≤ 1969 | 350 | 14 | 70 | 157 | 109 |
| 1970–1989 | 450 | 18 | 90 | 202 | 140 |
| 1990–2009 | 450 | 18 | 90 | 202 | 140 |
| 2010+ | 300 | 12 | 60 | 135 | 93 |
| **Total plancher** | **1 550** | **62** | **310** | **696** | **482** |
| Sièges libres | 450 | 18 | 90 | 204 | 118 |

Le 2010+ est volontairement le plus bas : le cliquet et les séries suivantes
rattrapent ceux qui explosent après le lancement. Le patrimoine a des sièges
garantis, il ne dépend pas d'un mois de pageviews.

## Recensement du vivier

Lancé le 20 octobre 2026 : `tools/census_vivier.py`, Wikidata uniquement
(occupation + MusicBrainz + `wikibase:sitelinks ≥ 6`), sans dumps de pageviews.

| | n |
|---|---:|
| Humains avec occupation + MBID + 6 sitelinks | 39 681 |
| Éligibles (genre jouable + musicien d'abord) | **22 481** |
| Genre absent | 12 214 |
| Genre exclu / hors familles | 2 851 |
| Célébrité non musicien | 2 135 |

Bandes (même découpage 3 / 15 / 50 / 80 %, d'abord proxy sitelinks puis
score personnel) : 714 icônes / 2 860 connus / 8 342 scène / 7 150 deep /
4 497 exclus. Le score a fait **bouger ~8 000 personnes** d'une bande à
l'autre. C'est précisément pourquoi le proxy ne suffisait pas.

**Tous les planchers tiennent**, y compris Latin (908), Afro (376) et les cases
deep de chaque famille. L'hypothèse « ~15 000 éligibles » est trop basse : on a
de la marge pour la Série 1 et plusieurs extensions avant de parler de
rééditions.

Le country, une fois le Q-ID jazz/country remis à l'endroit, retombe à
1 002. Les 12 214 sans `P136` se rattraperont en partie via MusicBrainz.

### Score personnel (septembre 2026)

`tools/score_vivier.py` : les cinq composantes (40 / 20 / 15 / 10 / 15) +
héritage λ = 0,40. Dump MusicBrainz du 17 octobre 2026 : 18 489 fiches
avec release-groups, 13 055 avec un groupe, 6 219 avec une date
d'appartenance. Contribution : 5 842 dates+albums, 377 dates seules,
16 262 au défaut 0,6. Richesse Wikidata complète (22 481, médiane 79,
4 886 avec au moins une récompense P166).

608 528 hits pageviews, 30 éditions, plancher de marché top 1 % (1 361).

Bandes après score : 674 icônes / 2 698 connus / 7 868 scène / 6 744 deep /
4 497 exclus.

Le signal de notoriété tient (Jackson, Elvis, Gaga, Lennon, Shakira en
tête ; Céline 8ᵉ, Miles 54ᵉ, Nina 165ᵉ, Aya 929ᵉ). Les graines de genres
ont été corrigées le 20 octobre 2026 (soul n'est plus du punk, jazz et
country ne sont plus inversés, J-pop n'est plus du reggae). Vote
majoritaire à la place du « premier genre spécifique gagne ». Filtre
célébrité : un acteur reste s'il a un métier musical fort (auteur,
rappeur…) ; Depp, Johansson, Zendaya, Mozart sortent. Jackson est classé
pop (override éditorial), Taylor Swift / Bieber / Shakira / J.Lo pop,
Ringo / Sting / Bono rock, Dalida chanson, Céline pop, Elvis rock, Nina
et Miles jazz. Pop rock et soft rock comptent désormais comme rock
(sinon Ringo et Collins tombaient en pop). Un artiste majoritairement
classique / gospel / expérimental est exclu au lieu de fuiter vers folk
ou latin (Liszt, Strauss). Country retombe de 3 201 à 1 002. Punk reste
au-dessus du plancher (87 / 65).

## Draft du 20 octobre 2026

`tools/draft_serie1.py` → `docs/serie-1-draft.csv`. 2 000 cartes.

Pour chaque bande : moitié des sièges au mieux classé (cœur), liste verte
des intouchables hors cœur (Hallyday, Miles, Nina, Fela, Aya…), puis
comblement des cases déficitaires, puis sièges libres. Le mélange
80 / 400 / 900 / 600 somme à 1 980 ; 20 sièges de rattrapage ferment
les planchers globaux (punk, Afrique, 2010+).

Tous les planchers genre / région / époque tiennent. Le top 40 du vivier
est entièrement dans le set. Coelho, Downey Jr. et Eddie Murphy sont
veto. Quelques cases *par bande* restent courtes (1 icône world, 1 icône
punk, 6 punk « connus ») : pas assez d'éligibles à ce palier, écart
tracé, pas de fiche fantôme.

Raretés dans la série : 48 diamants / 110 platines / 260 rares /
560 argents / 1 022 communes. Plus de palier légendaire.

## Plaque d'illustration

Chaque carte de `docs/serie-1-draft.csv` porte maintenant une clé `plaque` :

`style|instrument|pose|costume|venue|silhouette`

| Champ | Source | Rôle |
|---|---|---|
| silhouette | `P21` → f / m / x | Axe F/M des prompts |
| instrument | `P1303` → 8 familles | Famille de poses |
| pose | hash du Q-id, 1–7 | Variante dans la famille |
| costume | époque (4 tranches, 1960s par défaut pour pre-1970) | Tenue |
| venue | bande de notoriété | Décor |
| style | rareté dans la série | Sérigraphie / contre-jour / encre |

Collecte : `tools/fetch_illustration_attrs.py` puis `tools/attach_illustration.py`.
Les fiches brutes sont dans `data/census/illustration_raw.json`.

Série 1 : 1 377 m / 615 f / 8 x. 656 plaques distinctes pour 2 000 cartes
(sérigraphie 1 582, contre-jour 370, encre 48).

On ne génère pas 2 000 images. `python tools/illustration_prompts.py` sort
une liste de jobs (plaque + exécution A/B selon la rareté).
`python tools/generate_illustrations.py --lookdev` envoie six plaques de
contrôle à Fal.ai ; sans flag, il enchaîne le reste et saute ce qui existe
déjà dans `out/illustrations/`.

## Après la Série 1

- **Série 2** : le même algo sur le vivier restant, avec son propre quota de 80 icônes
  sorties de la réserve.
- **Extensions thématiques** (Jazz 1959, Métal 90s, Scène française) : elles ont encore
  des têtes d'affiche parce que la Série 1 ne les a pas toutes prises.
- **Rééditions** le jour où le vivier se tend : même personne, nouveau traitement,
  éventuellement palier monté par le cliquet. Voir le raisonnement « que faire des
  ~24 000 » : on ne descend pas dans le dernier quintile.
