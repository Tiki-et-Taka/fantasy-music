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
- Pour du volume, les dumps mensuels de pageviews sont plus efficaces que l'appel
  article par article.

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

Le job mensuel tourne sur GitHub Actions (gratuit sur dépôt public). Les visuels sont
pré-rendus en WebP/AVIF et poussés sur un stockage objet.

## Infrastructure cible

| Poste | Choix | Pourquoi |
|---|---|---|
| Stockage images | Cloudflare R2 | **Pas de frais d'egress** — c'est le poste qui explose si on le rate |
| CDN / app | Cloudflare Workers | Plan gratuit généreux |
| Base de données | Neon ou Supabase | Plan gratuit |
| Jobs de données | GitHub Actions | Gratuit sur dépôt public |

Ordre de grandeur : **0 à 20 €/mois** pour plusieurs milliers de joueurs.
