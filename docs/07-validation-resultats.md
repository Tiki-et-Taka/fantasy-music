# Résultats de la validation sur données réelles

Exécution : `python tools/validate_scoring.py` — 38 artistes et 7 groupes de référence,
données Wikidata, pageviews Wikimedia et MusicBrainz réelles.
Sortie brute : `data/validation.json`, journal : `data/run5.log`.

**Les 8 cas de référence passent.** Mais deux enseignements importants sont apparus, dont
une erreur dans ce que la spécification affirmait.

---

## 1. Erreur corrigée : l'héritage peut inverser l'ordre interne au groupe

`03-rarete-scoring.md` affirmait que le terme `max(0, score_groupe − score_perso)`
garantissait que « l'ordre interne au groupe est toujours préservé ». **C'est faux dès
que la contribution varie d'un membre à l'autre.**

Démonstration observée chez Slipknot :

| Membre | Score perso | Contribution | Gain | Score final |
|---|---:|---|---:|---:|
| Shawn Crahan | −0,92 | 0,6 *(défaut, dates absentes)* | 0,39 | **−0,52** |
| Craig Jones | −1,26 | 1,0 *(27 ans, dates présentes)* | 0,79 | **−0,46** |

Craig Jones part plus bas que Shawn Crahan et finit au-dessus. La garantie ne tient que
si la contribution est identique pour tous les membres.

Pire : ici l'écart de contribution est un **artefact de données manquantes**, pas un fait.
Crahan est lui aussi membre fondateur depuis 27 ans, mais Wikidata ne porte pas ses dates,
donc il hérite de la valeur par défaut 0,6 tandis que Jones obtient 1,0.

### Deux parades, à appliquer ensemble

**Parade de fond — combler les dates.** La cause racine est la couverture de
`P580`/`P582`, mesurée à 47 % (voir plus bas). Les relations d'artiste MusicBrainz sont
bien mieux renseignées : elles doivent devenir la source primaire, Wikidata le repli.

**Parade de sûreté — forcer la monotonie.** Après calcul, au sein de chaque groupe,
trier les membres par `score_perso` décroissant et contraindre `score_final` à être
non croissant dans cet ordre. Deux lignes de code, et la garantie devient structurelle
au lieu d'être une propriété espérée.

---

## 2. Couverture des champs Wikidata

Mesurée sur l'échantillon. **À lire comme une borne haute** : ces 38 artistes sont
volontairement très célèbres, donc mieux renseignés que la moyenne d'une Série 1.

| Champ | Couverture | Verdict |
|---|---:|---|
| `P136` genre | 100 % | La couche palette est alimentable |
| `P2031` début d'activité | 100 % | La couche costume est alimentable |
| `P434` identifiant MusicBrainz | 100 % | La jointure vers MusicBrainz est fiable |
| `P1303` instrument | 97 % | La couche pose est alimentable |
| `P463` appartenance | 90 % | Suffisant |
| **`P580`/`P582` dates d'appartenance** | **47 %** | **Insuffisant — bloque la contribution** |

Un seul champ pose problème, et c'est précisément celui dont dépend l'héritage.

---

## 3. Le biais anglophone est mesurable

Les pageviews n'ont pu être collectés que sur l'édition anglophone (voir section 4).
Conséquence immédiate et parlante : **Aya Nakamura ressort au rang 31 sur 38**, alors
qu'elle est l'une des artistes les plus écoutées de France.

C'est la démonstration concrète du risque déjà identifié dans `04-distribution.md` :
prendre le top N par score produit un set massivement anglo-saxon.

**Correctif décidé à la suite de cette mesure :** le problème ne vient pas de la source
mais de l'agrégation. Sommer les vues brutes revient à ne mesurer que l'édition
anglophone, qui pèse un ordre de grandeur de plus que les autres. On passe donc à une
**part par communauté linguistique** pondérée par `√(V_w)`, complétée d'un bonus
d'entropie et d'un plancher de domination de marché — formule complète dans
[`03-rarete-scoring.md`](03-rarete-scoring.md).

Les quotas de curation par pays et par genre restent nécessaires par ailleurs : aucune
formule ne produira spontanément un set équilibré.

---

## 4. L'API pageviews n'est pas utilisable à l'échelle

Enseignement technique majeur, obtenu à la dure.

L'API REST `wikimedia.org/api/rest_v1` renvoie des **HTTP 429** pour un client anonyme
bien avant les limites annoncées : environ 100 requêtes consécutives, même espacées de
1,2 s, puis un blocage de l'ordre de la minute — et les blocages s'allongent quand on
insiste.

Or une Série 1 de 2 000 artistes × 50 langues représente **100 000 requêtes**.
C'est hors de portée.

**Décision : passer par les dumps mensuels de pageviews** (`dumps.wikimedia.org`,
`pageviews-YYYYMM-user.bz2`). Un fichier par mois, tous projets et tous articles
confondus, filtré en local. Zéro requête API, zéro limitation.

Piège à anticiper dans le script définitif : un échec réseau ne doit **jamais** être
converti en zéro. Une première version le faisait et attribuait silencieusement zéro vue
à Paul McCartney et Metallica, ce qui plaçait Joey Jordison en tête de Slipknot. Un échec
doit rester une valeur manquante explicite.

---

## 5. Ce que le classement confirme

Le haut du classement est crédible : Lennon, McCartney, Starr, Cobain, Björk, Miles
Davis. Le bas aussi : Ron McGovney finit 37ᵉ sur 38.

| Cas | Résultat |
|---|---|
| Mike Portnoy (−0,19) ≥ James LaBrie (−0,75) | Aucun poids de rôle ne s'est glissé dans le calcul |
| Marilyn Manson (+0,76) > John 5 (−0,46) | L'héritage remonte sans inverser |
| John 5 : −0,59 → −0,46 | L'héritage agit effectivement |
| Corey Taylor en tête de Slipknot | Le frontman ressort par ses seules données |
| Dave Mustaine 16ᵉ/38 | Haut palier malgré 14 mois chez Metallica, sans filtre d'ancienneté |
| Ron McGovney 37ᵉ/38 | L'héritage ne hisse pas un membre marginal |
| Pete Best (+0,15) < Ringo Starr (+1,60) | Le batteur viré reste sous son remplaçant |

**Les pondérations 45/25/15/15 et λ = 0,40 peuvent être conservées** comme point de
départ. Elles ne pourront être réellement calibrées qu'une fois les pageviews
multilingues disponibles via les dumps.

---

## Suite

1. Implémenter la contrainte de monotonie intra-groupe.
2. Brancher MusicBrainz comme source primaire des dates d'appartenance, puis remesurer
   la couverture.
3. Remplacer l'API pageviews par les dumps mensuels.
4. Rejouer la validation, puis passer à l'extraction large pour caler les centiles.
