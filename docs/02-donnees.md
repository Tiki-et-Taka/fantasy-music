# Données et sources

## Sources retenues

### Wikidata — colonne vertébrale

CC0, donc aucune contrainte d'usage commercial ni d'attribution obligatoire. C'est
surtout le hub d'identifiants vers tout le reste.

Propriétés utilisées :

| Propriété | Usage |
|---|---|
| `P31 = Q5` | Filtre « être humain » |
| `P106` | Occupation (chanteur, musicien, rappeur, compositeur…) |
| `P1303` | Instrument → pilote la pose de l'illustration |
| `P21` | Sexe / genre → silhouette f / m / x de la plaque |
| `P463` / `P527` | Membre de / a pour partie, avec qualificatifs `P580` et `P582` pour les dates, parfois `P2868` pour le rôle |
| `P569` / `P570` | Naissance / décès |
| `P2031` | Début de période d'activité |
| `P27` | Nationalité |
| `P136` | Genre musical → pilote la palette |
| `P166` | Récompenses → entre dans le score |
| `P434` | Identifiant MusicBrainz, clé de jointure |

**Contrainte technique :** l'endpoint SPARQL public coupe à 60 s. Découper par
nationalité ou par décennie, ou travailler sur un dump JSON filtré.

### MusicBrainz — structure et discographie

Données cœur en CC0. Nettement plus fiable que Wikidata sur la **composition des
groupes et les dates d'appartenance**, qui sont lacunaires côté Wikidata. À prendre
comme source primaire pour ces champs.

- API publique limitée à 1 requête/seconde → pour du volume, monter le dump Postgres
  en local via `musicbrainz-docker`.
- Attention : les *annotations* sont en CC BY-NC-SA, et les images du Cover Art Archive
  ne sont pas librement réutilisables.

### ListenBrainz — statistiques d'écoute

Données d'écoute réelles en CC0. C'est l'alternative juridiquement propre à Spotify et
Last.fm.

### API Pageviews de Wikimedia

Gratuite, sans clé.

```
https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/
  {projet}/all-access/user/{titre}/monthly/{debut}/{fin}
```

- Toujours utiliser le filtre `user` (exclut les bots).
- User-Agent identifiable obligatoire.

> ⚠ **Mesuré en conditions réelles : cette API est inutilisable à l'échelle.** Pour un
> client anonyme elle renvoie des HTTP 429 après une centaine de requêtes consécutives,
> même espacées de 1,2 s, avec des blocages de l'ordre de la minute qui s'allongent si
> l'on insiste. Une Série 1 de 2 000 artistes × 50 langues représente 100 000 requêtes :
> hors de portée.
>
> **Décision : passer par les dumps mensuels** (`dumps.wikimedia.org`,
> `pageviews-YYYYMM-user.bz2`), filtrés en local. L'API ne reste bonne que pour des
> vérifications ponctuelles. Détails dans
> [`07-validation-resultats.md`](07-validation-resultats.md).

### Wikimedia Commons

Utilisable uniquement pour des éléments non liés à une personne. La licence s'obtient
via l'API Commons (`prop=imageinfo&iiprop=extmetadata`). Rappel : une licence libre ne
règle **pas** le droit à l'image (voir `01-cadre-juridique.md`).

## Sources écartées

| Source | Raison |
|---|---|
| **Spotify** | Les Developer Terms restreignent plusieurs usages commerciaux, imposent des règles strictes sur les images d'artistes et sur la durée de cache. Construire une économie dessus expose à une coupure unilatérale. |
| **Last.fm** | API gratuite en non-commercial uniquement ; licence payante au-delà. |
| **Discogs** | Images non réutilisables, accès restreint. |
| **Getty, AP, photos de presse** | Hors de question. |

## Architecture du pipeline

Tout se calcule **hors ligne**. Le jeu en production ne requête jamais Wikidata ni
MusicBrainz en direct : il lit un dataset figé.

```
Wikidata (SPARQL / dump)  ─┐
MusicBrainz (dump Postgres)─┼─→  job mensuel  ─→  dataset figé  ─→  jeu
Pageviews (dumps mensuels) ─┤      (scoring,         (JSON/SQLite)
ListenBrainz               ─┘   résolution genre,
                                 génération visuels)
```

Le schéma du dataset figé (cartes, séries, appartenances, historique de rareté)
est défini dans [`09-schema-donnees.md`](09-schema-donnees.md) et
[`data/schema/`](../data/schema/). Runbook complet :
[`10-pipeline.md`](10-pipeline.md).

```
python tools/run_pipeline.py --stage all-light
python tools/export_catalog.py --sqlite --validate
```

→ `data/census/catalog_s1.json` (+ `.sqlite`).

La **validation** du schéma tourne sur GitHub Actions (cron mensuel + PR).
L’ingest des dumps pageviews (~6 Go/mois) reste **local ou self-hosted**.
Les visuels sont pré-rendus en WebP (`tools/prerender_illustrations.py`) puis
poussés sur un stockage objet.

## Infrastructure cible

| Poste | Choix | Pourquoi |
|---|---|---|
| Stockage images | Cloudflare R2 | **Pas de frais d'egress** — c'est le poste qui explose si on le rate |
| CDN / app | Cloudflare Workers | Plan gratuit généreux |
| Base de données | Neon ou Supabase | Plan gratuit |
| Jobs de données | GitHub Actions | Gratuit sur dépôt public |

Ordre de grandeur : **0 à 20 €/mois** pour plusieurs milliers de joueurs.
