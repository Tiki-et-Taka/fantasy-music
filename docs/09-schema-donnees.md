# Schéma de données

Source de vérité pour le **catalogue figé** (pipeline hors ligne) et un appendice
**état joueur** (ce que le prototype stocke déjà en `localStorage`). Les définitions
machine-lisibles sont dans [`data/schema/`](../data/schema/).

Hors périmètre : marché / listings (brique 2), groupes fantasy (brique 3).
Pipeline opérationnel : [`10-pipeline.md`](10-pipeline.md).

## Principes

1. **Identifiants stables.** Artiste = Q-id Wikidata. Carte = `{series_id}:{qid}`
   (ex. `s1:Q2831`). Jamais le nom affiché comme clé.
2. **Catalogue figé en lecture.** Le jeu en prod ne recalcule pas le score : il lit
   le dataset publié (JSON ou SQLite). Voir [`02-donnees.md`](02-donnees.md).
3. **Cliquet = historique.** La rareté affichée ne descend jamais ; chaque promotion
   est une ligne d’historique. Formule dans [`03-rarete-scoring.md`](03-rarete-scoring.md).

## Paliers de rareté

Ordre total (croissant) :

| Rang | Valeur stockée |
|---:|---|
| 0 | `commune` |
| 1 | `argent` |
| 2 | `or` |
| 3 | `platine` |
| 4 | `diamant` |

Invariant : `rank(rarity_current) >= rank(rarity_initial)`.

## Entités catalogue

### Series

Une édition publiée du set (Série 1, Série 2, extension thématique…).

| Champ | Type | Notes |
|---|---|---|
| `id` | string PK | Ex. `s1` |
| `name` | string | Affichage |
| `size` | int | Cartes prévues (2 000 pour S1) |
| `released_at` | date \| null | Null tant que non publiée |
| `status` | string | `draft` \| `released` \| `archived` |

### Artist

Personne réelle, une fiche vivier / scoring — indépendante des séries.

| Champ | Type | Notes |
|---|---|---|
| `qid` | string PK | Wikidata, ex. `Q2831` |
| `mbid` | string \| null | MusicBrainz artist UUID |
| `name` | string | Nom d’affichage (sans désambiguïsation Wikipédia) |
| `sex` | string \| null | `f` \| `m` \| `x` (silhouette plaque) |
| `instrument` | string \| null | Famille d’instrument (8 valeurs) |

Les scores bruts (pageviews, sitelinks, etc.) restent dans les artefacts de scoring
(`data/census/…`) ; le catalogue jeu n’en a pas besoin au runtime.

### Group

Groupe musical (entité MusicBrainz), pour les appartenances et le bandeau « groupe ».

| Champ | Type | Notes |
|---|---|---|
| `mbid` | string PK | MusicBrainz |
| `name` | string | Nom d’affichage |
| `qid` | string \| null | Wikidata du groupe si connu |

### Membership

Appartenance artiste ↔ groupe, source primaire MusicBrainz.

| Champ | Type | Notes |
|---|---|---|
| `artist_qid` | string FK | → Artist |
| `group_mbid` | string FK | → Group |
| `start` | date \| null | |
| `end` | date \| null | Null = en cours / inconnu |
| `is_primary` | bool | Groupe affiché sur la carte S1 si plusieurs |

Clé primaire : `(artist_qid, group_mbid)`.

### Plate

Plaque d’illustration partagée (pas une image par carte).

| Champ | Type | Notes |
|---|---|---|
| `id` | string PK | Ex. `encre\|voix\|4\|1970s80s\|stade\|m` (même clé que le draft) |
| `style` | string | `serigraphie` \| `contrejour` \| `encre` |
| `instrument` | string | |
| `pose` | int | 1–7 |
| `costume` | string | Tranche d’époque / tenue |
| `venue` | string | Décor |
| `sil` | string | `f` \| `m` \| `x` |
| `path` | string \| null | Chemin relatif sous `out/illustrations/` |

### Card

Une carte = un artiste **dans une série**. C’est l’unité collectionnable.

| Champ | Type | Notes |
|---|---|---|
| `id` | string PK | `{series_id}:{qid}` |
| `series_id` | string FK | → Series |
| `artist_qid` | string FK | → Artist |
| `rank_in_series` | int | 1…N dans la série |
| `rank_vivier` | int \| null | Rang au moment du draft |
| `rarity_initial` | string | Palier à la sortie de la série |
| `rarity_current` | string | Palier affiché (= max historique) |
| `family` | string | Famille de genre (clé canonique) |
| `band` | string | Bande de draft : `icones` \| `connus` \| … |
| `region` | string \| null | |
| `era` | string \| null | |
| `motif` | string \| null | Raison de draft |
| `plate_id` | string FK | → Plate |
| `group_mbid` | string \| null FK | Groupe affiché (dénormalisé pour le bandeau) |
| `in_booster_pool` | bool | False si sortie du pool après promotion cliquet |

Unicité : `(series_id, artist_qid)` — une seule carte par artiste et par série.

À la publication de la Série 1 : `rarity_current = rarity_initial`,
`in_booster_pool = true`, aucun `RarityEvent`.

### RarityEvent

Historique du cliquet. Sans cette table, on ne peut pas auditer ni rejouer une
promotion.

| Champ | Type | Notes |
|---|---|---|
| `id` | int PK | Autoincrement |
| `card_id` | string FK | → Card |
| `from_rarity` | string | |
| `to_rarity` | string | Strictement supérieur |
| `series_boundary` | string | Id de la série / fenêtre qui déclenche (ex. `s2`) |
| `effective_at` | date | |
| `reason` | string | Ex. `two_quarters_above_threshold` |

#### Règles du cliquet (modélisées)

```
rarity_displayed = max(rarity_initial, rarity_recalculated)
```

- Promotion **uniquement** aux frontières de série.
- Signal soutenu : **deux trimestres** consécutifs au-dessus du seuil, sur la
  médiane 24 mois (détail scoring dans `03-rarete-scoring.md`).
- À chaque promotion : écrire un `RarityEvent`, mettre à jour `rarity_current`,
  passer `in_booster_pool` à `false` pour cette carte (elle ne revient pas dans
  les boosters futurs au ancien palier ; la nouvelle série peut la réimprimer).

Variante future « Ascension / chevron » (carte garde le palier d’origine + badge) :
**non modélisée** ici.

## Mapping depuis le draft actuel

Sources : [`docs/serie-1-draft.csv`](serie-1-draft.csv) (humain) et
`data/census/serie1.json` (machine, contient le `qid`).

| Draft / slim | Schéma |
|---|---|
| *(implicite)* `s1` | `Series.id` |
| `qid` (JSON) | `Artist.qid`, `Card.artist_qid`, suffixe de `Card.id` |
| `rang_serie` | `Card.rank_in_series` |
| `rang_vivier` | `Card.rank_vivier` |
| `rarete` | `Card.rarity_initial` **et** `Card.rarity_current` |
| `artiste` | `Artist.name` |
| `groupe` (libellé) | À résoudre vers `Group` / `Card.group_mbid` via MusicBrainz |
| `famille` (libellé FR CSV) / `family` (clé JSON) | `Card.family` — **préférer la clé** (`pop`, `rock`…) |
| `bande` / `band` | `Card.band` |
| `region` | `Card.region` |
| `epoque` / `era` | `Card.era` |
| `sexe` / `silhouette` | `Artist.sex` |
| `instrument` | `Artist.instrument` + axe plaque |
| `plaque` | `Plate.id` + `Card.plate_id` |
| `motif` / `draft_reason` | `Card.motif` |

Le CSV seul ne suffit pas à peupler le schéma : le **Q-id** est obligatoire et
vit dans `serie1.json` (ou une jointure nom → qid via `qid_titles.json`).

## Appendice joueur

Aligné sur [`prototypes/booster.html`](../prototypes/booster.html)
(`charts.s1.owned`, `charts.s1.wallet`). Pas d’implémentation runtime dans cette
étape ; cible future Neon / Supabase.

### OwnedCopy

| Champ | Type | Notes |
|---|---|---|
| `user_id` | string | Compte (proto : implicite / appareil) |
| `card_id` | string FK | → Card — **pas** le nom |
| `qty` | int | ≥ 1 |
| `acquired_at` | timestamptz | Dernière acquisition |
| `fresh` | bool | Non consultée dans le classeur |

Clé : `(user_id, card_id)`.

### Wallet

| Champ | Type | Notes |
|---|---|---|
| `user_id` | string PK | |
| `credits` | int | Monnaie unique (crédits) |
| `packs` | int | Boosters en stock |
| `last_daily` | date \| null | Dernier +1 quotidien |
| `starter` | bool | Pack de démarrage déjà versé |

## Fichiers machine

| Fichier | Rôle |
|---|---|
| [`data/schema/catalog.sql`](../data/schema/catalog.sql) | DDL SQLite catalogue |
| [`data/schema/catalog.schema.json`](../data/schema/catalog.schema.json) | JSON Schema d’export catalogue |
| `data/census/catalog_s1.json` | Export Série 1 (généré, gitignoré) |
| `data/census/catalog_s1.sqlite` | Idem, option `--sqlite` |

### Export

```
python tools/export_catalog.py
python tools/export_catalog.py --sqlite --validate
```

Lit `serie1.json` + titres + MusicBrainz / mbids, écrit le catalogue conforme au
schéma. Le prototype [`prototypes/booster.html`](../prototypes/booster.html)
charge `catalog_s1.json` (clés d’ownership = `card_id`).

L’appendice joueur est documenté ici et esquissé en commentaires SQL ; pas de
JSON Schema joueur tant que l’auth n’existe pas.
