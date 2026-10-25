# Pipeline technique

Runbook du dataset figé : pageviews → score → draft → catalogue → visuels.
Schéma : [`09-schema-donnees.md`](09-schema-donnees.md).

## Vue d’ensemble

```
dumps pageviews (mensuels)  ─┐
allowlist titres (vivier)   ─┼─→ aggregate (médiane) ─→ score_vivier
MusicBrainz + richesse WD   ─┘                              │
                                                            ▼
                                              draft_serie1 → export_catalog
                                                            │
plaques PNG (Fal / Flux)  ─→ prerender (WebP[/AVIF]) ←──────┘
```

Le jeu en prod lit `catalog_s1.json` / SQLite + images pré-rendues ; il ne
requête jamais Wikidata ni les dumps.

## Commandes

Orchestrateur :

```bash
python tools/run_pipeline.py --stage validate
python tools/run_pipeline.py --stage all-light          # aggregate + export + prerender + validate
python tools/run_pipeline.py --stage pageviews --months 2026-04,2026-05,2026-06,2026-07,2026-08,2026-09
python tools/run_pipeline.py --stage aggregate
python tools/run_pipeline.py --stage export
python tools/run_pipeline.py --stage prerender
```

### Pageviews multi-mois

1. Allowlist titres (une fois / quand le vivier change) :
   `python tools/build_census_allowlist.py`
2. Ingest (≈ 6 Go / mois, disque + bande passante) :
   `python tools/ingest_pageviews_dump.py --months 2026-04,…,2026-09`
3. Médiane :
   `python tools/aggregate_pageviews.py`
4. Rescore :
   `python tools/score_vivier.py`  
   (lit `data/pageviews/aggregate.json` s’il existe, sinon le mois le plus récent)

Un seul mois suffit à valider la formule ; **6 mois** pour calibrer ; **24** pour
figer la prod (médiane anti-pics). Les dumps ne sont pas commités.

### Catalogue

```bash
python tools/export_catalog.py --sqlite --validate
```

→ `data/census/catalog_s1.json` (+ `.sqlite`). Le prototype booster charge ce JSON.

### Pré-rendu visuels

```bash
python tools/prerender_illustrations.py
python tools/prerender_illustrations.py --avif   # si pillow-heif
```

PNG source dans `out/illustrations/` ; WebP dans `out/illustrations/webp/`.

## GitHub Actions

Workflow [`.github/workflows/pipeline.yml`](../.github/workflows/pipeline.yml) :

| Déclencheur | Rôle |
|---|---|
| push / PR (schema, tools) | `validate` — JSON Schema + DDL SQLite |
| cron mensuel (2 du mois) | même validation (garde-fou) |
| `workflow_dispatch` | `validate` / `export` / `prerender` / `all-light` |

**Les dumps pageviews ne tournent pas sur les runners gratuits** (taille + durée).
Ingest + score lourds : machine locale ou runner **self-hosted** avec le dossier
`data/` monté, puis commit / push des artefacts dérivés voulus (pas les dumps bruts).

## Ordre mensuel recommandé (prod)

1. Ingest le mois M-1 de pageviews.
2. `aggregate_pageviews.py` sur la fenêtre retenue (6 puis 24).
3. `score_vivier.py` si on recalibre ; sinon skip jusqu’à frontière de série.
4. À frontière de série seulement : draft → export → cliquet (`RarityEvent`).
5. Générer / corriger plaques manquantes → `prerender_illustrations.py`.
6. Publier catalogue + WebP sur le stockage objet (R2).
