# Brique 1 — reste à faire

## Tranché

- Sources de données retenues et écartées.
- Score composite 40 / 20 / 15 / 10 / 15 (pageviews / sitelinks / entropie /
  richesse Wikidata / discographie).
- Héritage de groupe sans poids de rôle, λ = 0,40, contribution à double branche.
- Critères d'éligibilité, sans filtre d'ancienneté, plafond de sécurité à 15 membres.
- Cliquet de rareté et ses garde-fous.
- Structure du booster à slots, taux de tirage, pity timer.
- Volumétrie des cinq paliers.
- Série 1 : 2 000 artistes, mélange 80 / 400 / 900 / 600. Voir
  [`08-serie-1.md`](08-serie-1.md).
- Cadre juridique : aucune photo, aucun visage identifiable, portraits en opt-in
uniquement, procédure de retrait, pas d'argent réel en entrée ni en sortie.
- Trois styles d'illustration et leur escalade par rareté.
- Sept couches de composition.
- Sceau de groupe génératif.
- Dix-sept familles de genres (gospel, classique et expérimental exclus).



## Chemin critique — validation sur données réelles

- [x] Extraire Wikidata + pageviews sur un échantillon ciblé de 38 artistes et
  ```
  7 groupes — `tools/validate_scoring.py`.
  ```
- [x] Vérifier le classement contre les cas de référence : **8/8 validés**.
- [x] Mesurer la couverture des champs.
- [x] Corriger les quatre points listés ci-dessous.
- [x] Recenser le vivier (Wikidata + sitelinks, sans dumps) :
  ```
  `tools/census_vivier.py` → 22 481 éligibles. Tous les planchers Série 1 tiennent,
  y compris les cases deep. Détail dans [`08-serie-1.md`](08-serie-1.md).
  ```
- [x] Rejouer le scoring sur le vivier (5 composantes + héritage).
  ```
  `tools/score_vivier.py` : pageviews 40 %, sitelinks 20 %, entropie 15 %,
  richesse Wikidata 10 %, discographie 15 %, héritage λ=0,40 (années et albums).
  Les pondérations restent des hypothèses à caler sur la draft.
  ```

Résultats détaillés dans `[07-validation-resultats.md](07-validation-resultats.md)`.

### Corrections issues de la validation

- [x] **Monotonie intra-groupe.** Implémentée dans `enforce_band_monotonicity()` ;
  4 inversions rattrapées sur l'échantillon de référence. L'héritage pouvait inverser
  l'ordre interne quand la
  ```
  contribution varie d'un membre à l'autre. Contraindre `score_final` à être non
  croissant dans l'ordre de `score_perso` au sein de chaque groupe.
  ```
- [x] **Dates d'appartenance et discographie MusicBrainz.** Dump 2026-10-17,
  ```
  `tools/ingest_musicbrainz_dump.py` + `tools/attach_group_albums.py`.
  18 489 fiches avec release-groups, 13 055 avec au moins un groupe,
  6 219 avec une date d'appartenance. Branche albums : 12 255 appartenances
  datées avec un catalogue de groupe, 10 931 avec au moins un album joué.
  Richesse Wikidata : 22 481/22 481 (`tools/fetch_wikidata_richness.py`,
  statements + identifiants + P166).
  ```
- [x] **Pageviews par dumps.** Pipeline validé sur septembre 2026 (6,33 Go, 30
  éditions, 3 654 hits). L'API REST est inutilisable à l'échelle. Les autres mois
  (6 puis 24) sont **reportés à la construction du catalogue** : un mois suffit à
  valider la formule, plusieurs mois ne servent qu'à écraser les pics en production.
- [x] **Normalisation des pageviews par édition.** Implémentée sur le vivier
  ```
  (`tools/score_vivier.py`, dump 2026-09). Part √(V_w) × vues/médiane_musiciens,
  bonus d'entropie `max(0, z)`, plancher top 1 % (1 361 artistes). Après les
  cinq composantes : Aya Nakamura 929ᵉ, Miles Davis 54ᵉ, Nina Simone 165ᵉ —
  le patrimoine ne s'écroule pas.
  ```



## Décisions ouvertes

- [x] **Taille de la Série 1.** 2 000, mélange 80 / 400 / 900 / 600.
- [x] **Planchers genre / région / époque.** Figés dans
  [`08-serie-1.md`](08-serie-1.md) (1 385 / 1 480 / 1 550), tranchés comme le set.
- [ ] Découpage en extensions et rythme de sortie.



## À produire

Par ordre d'urgence :

- [x] **Sexe et instrument pour les plaques.** `P21` + `P1303` collectés
  ```
  sur tout le vivier (`tools/fetch_illustration_attrs.py`). Silhouette
  f/m/x et famille d'instrument accrochées au ranking et à la Série 1
  (`tools/attach_illustration.py`). Sans ça, pas de rattachement prompt ↔ carte.
  ```
- [x] **Batch d'illustrations.** `tools/illustration_prompts.py` déduplique
  ```
  le draft en plaques (pas 2 000 prompts). `tools/generate_illustrations.py`
  les envoie à Flux Schnell (Fal.ai). `--lookdev` pour les 6 de validation,
  puis le reste sans clic.
  ```
- [~] **Planche de validation sérigraphie** — *caduc.* Les plaques sont générées
  ```
  en IA à l’échelle du set ; plus de commande illustrateur ni de planche de
  six avant go.
  ```
- [~] **Brief illustrateur détaillé** — *caduc.* Même raison (pipeline IA /
  ```
  Flux). La DA reste dans `05-direction-artistique.md`.
  ```
- [x] **Draft Série 1.** `tools/draft_serie1.py` → 2 000 cartes,
  ```
  `docs/serie-1-draft.csv`. Planchers tenus, top 40 du vivier assis,
  raretés calées dans la série. Listes verte/rouge dans
  `tools/draft_lists.json`.
  ```
- [x] **Graines de genres + filtre « musicien d'abord ».** IDs Wikidata
  ```
  corrigés, vote majoritaire, acteurs sans métier musical fort exclus
  (~2 100 rejets). Jackson/Céline/Elvis/Nina/Miles sont cohérents ; Mozart,
  Depp, Johansson, Zendaya hors vivier. Une table d'override fine reste
  utile (Dylan encore country, quelques icônes mal taguées) mais n'est
  plus bloquante.
  ```
- [x] **Schéma de données** — carte, série, appartenances, plaques, historique
  ```
  de rareté (cliquet). Spec `docs/09-schema-donnees.md` +
  `data/schema/catalog.sql` + `data/schema/catalog.schema.json`.
  ```
- [x] **Pipeline technique** — runbook [`10-pipeline.md`](10-pipeline.md) :
  ```
  aggregate multi-mois (`aggregate_pageviews.py`), scoring branché sur
  l’agrégat, export catalogue, pré-rendu WebP, orchestrateur
  `run_pipeline.py`, workflow Actions (validate mensuel). Les dumps
  pageviews additionnels se lancent en local / self-hosted (taille).
  ```
- [x] **Pages légales (minimum)** — `prototypes/legal/` : mentions, taux,
  ```
  données personnelles (RGPD).
  ```
- [ ] **Avant prod — compléter les pages légales**
  ```
  - éditeur + hébergeur (mentions) ;
  - remplacer `privacy@example.com`.
  ```



## Hors brique 1

- Brique 2 — économie : monnaie + marché prix fixe amorcés dans le proto
  (`docs/11-marche.md`) ; pas de craft — reste anti-bot comptes, historique.
- Brique 3 — boucle de jeu : constituer des groupes fantasy ; le score de compétition
  est la somme des écoutes hebdomadaires des membres. *Ébauche, pas encore spécifiée.*
- [ ] **Version anglaise du site** (UI + pages légales), après stabilisation du français.



## Marché (brique 2) — tranché

- **Prix fixe** (annonce = carte + prix en crédits). Pas d’enchères au lancement.
- Enchères éventuelles plus tard (diamants / événements), hors socle.

