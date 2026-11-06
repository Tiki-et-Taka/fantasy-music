# Fantasy Game — règles (brique 3)

Tranché le 27 octobre 2026.

## Idée

Chaque joueur compose un **groupe de 5 musiciens** à partir de ses cartes.
Chaque semaine, le score du joueur est la somme des **formes relatives** de ses
cinq postes, calculées à partir d’**écoutes réelles** (ListenBrainz, CC0).
Le classement oppose les joueurs.

## Formation

| Poste | Familles d’instrument éligibles |
|-------|----------------------------------|
| 1 chanteur | `voix` |
| 1 basse | `basse`, **`machines`** |
| 1 batterie | `batterie`, **`machines`** |
| 2 mélodiques | `guitare`, `claviers`, **`machines`**, `vents`, `cordes` |

**`machines` est un joker** : une même carte machines peut occuper le poste basse,
batterie **ou** mélodique (un seul poste à la fois). Elle ne remplace pas le
chanteur (`voix`).

**Voix + secondaire** : certains artistes restent `voix` en primaire (plaque /
rareté) mais gagnent un ou plusieurs instruments secondaires pour l’éligibilité
Fantasy (ex. Ed Sheeran → voix + guitare). Les chanteurs unilatéraux (ex. Michael
Jackson) restent voix seuls. Arbitrage auto :
[`tools/triage_voix_dual.py`](../tools/triage_voix_dual.py) →
[`data/census/instrument_extra.json`](../data/census/instrument_extra.json) et
[`docs/voix-instrument-arbitrage.csv`](voix-instrument-arbitrage.csv)
(artiste + secondaire ; détail technique dans `voix-instrument-arbitrage-detail.csv`).

La médiane de forme d’un poste inclut tous les artistes du catalogue **éligibles
à ce poste** (donc les `machines` et les secondaires voix+X).

Contraintes :

- cartes **possédées** uniquement ;
- **un seul exemplaire** d’un `cardId` dans le lineup (les doublons ne se cumulent pas) ;
- **au plus une carte diamant** dans le lineup ;
- les deux postes mélodiques sont distincts (deux cartes, pas deux fois la même).

## Marché — verrou lineup

Une carte présente dans le lineup est **bloquée à la vente, à l’échange et à la
défausse** jusqu’à la prochaine fenêtre de transfert (même logique que « exemplaire
déjà en annonce ») : elle consomme une copie « libre ».

Retirer la carte du lineup (pendant la fenêtre ouverte) la libère immédiatement.

## Calendrier

1. **Fenêtre de transfert** — édition libre du lineup.
2. **Lock** — typiquement lundi 00:00 (heure du serveur) : lineup figée pour la semaine ISO en cours.
3. **Semaine d’écoutes** — agrégation ListenBrainz sur 7 jours, clé `mbid` artiste.
4. **Score + classement** — publication en fin de semaine.
5. **Récompenses** — crédits / booster (barème produit, hors proto).

## Score — relatif par poste

Pas de somme brute des écoutes (les stars `voix` écraseraient le board).

Pour chaque poste `p` du lineup :

```
contrib(p) = listens(artiste) / mediane(listens de tous les artistes
             du catalogue éligibles au poste p, cette semaine)
```

- artiste sans signal ListenBrainz → `contrib = 0` (pas de remplacement auto) ;
- score joueur = somme des 5 `contrib` ;
- l’UI peut afficher les écoutes brutes **et** la forme du poste.

Variante équivalente acceptée plus tard : percentile 0–100 dans le pool du poste.

## Données ListenBrainz

- Identifiant d’écoute : MBID **crédité** (groupe ou artiste solo), pas
  forcément le MBID perso du musicien.
- Rattachement : chaque artiste du vivier → son/ses groupes MusicBrainz
  (`member of band`, dates + `albums_played` / `albums_total` via
  [`tools/attach_group_albums.py`](../tools/attach_group_albums.py)).
  Solo sans groupe : ses propres écoutes (poids 1).
- **Attribution (option 2)** — pas de partage entre coéquipiers ; chaque
  membre reçoit sa propre fraction du signal groupe :

  ```
  listens_membre += listens_groupe × poids
  ```

  avec `poids` par lien groupe :
  1. **dates + `albums_total` > 0** → `albums_played / albums_total`
     (albums studio dont l’année ∈ [start, end]) ;
  2. **appartenance sans dates** (MB lacunaire) → **poids 1** : on crédite
     tout le signal groupe plutôt que de zéroter un vrai membre ;
  3. **dates OK mais `albums_played` = 0** (fenêtre sans album studio) →
     poids 0 pour ce lien.

  Somme sur tous les groupes rattachés. Solo sans groupe : poids 1 sur
  ses propres écoutes. Deux cartes du même groupe dans un lineup cumulent
  deux fois **leur** fraction.
- Job hebdo (prod) : listens 7 jours par MBID crédit → cache versionné →
  projection sur les cartes via le rattachement pondéré.
- Proto : fixtures / pseudo-aléatoire déterministe par `mbid` + semaine ISO.
- **Mis de côté (pas retirés du vivier)** : artistes sans signal ListenBrainz
  (popularité all-time nulle sur MBID perso **et** groupes rattachés). Liste
  versionnée [`data/census/fantasy_listen_aside.json`](../data/census/fantasy_listen_aside.json),
  produite par [`tools/probe_listenbrainz_coverage.py`](../tools/probe_listenbrainz_coverage.py).
  Ils restent dans `eligible.json` (rareté / draft / autre source future) mais
  sont **hors pool Fantasy écoutes** tant qu’ils figurent dans ce fichier.
- **Faux musiciens (retirés du vivier)** : célébrités / écrivains / monarques à
  discographie perso faible et sans vrai ancrage de groupe — Seagal, Coelho,
  etc. Purge : [`tools/purge_fake_musicians.py`](../tools/purge_fake_musicians.py)
  → [`data/census/fake_musicians_purged.json`](../data/census/fake_musicians_purged.json).
  Le filtre célébrité du census s’applique désormais à **toutes** les familles.

Les écoutes **ne** reentrent **pas** dans le scoring de rareté des cartes
(voir [`03-rarete-scoring.md`](03-rarete-scoring.md)) : récence voulue ici, écartée là-bas.

## Déséquilibre voix / basse

Pool S1 initial : `voix` très majoritaire, `basse` et `batterie` rares.
Cause structurelle : le vivier exige des **sitelinks Wiki perso** élevés ; les
rhythm sections de groupes cultes ont souvent une fiche pauvre alors que le
chanteur passe le seuil. L’héritage de groupe (scoring) ne s’applique qu’**après**
l’admission — trop tard pour eux.

Correctifs retenus (sans poids de rôle sur la rareté) :

1. **Admission coattail MusicBrainz** — `python tools/coattail_rhythm.py --merge` :
   pour chaque groupe ancré par un membre déjà `icones`/`connus` (ou sitelinks
   élevés), admettre les autres membres `basse`/`batterie` même sous le seuil
   sitelinks standard (`coattail_rhythm` dans [`tools/census_config.json`](../tools/census_config.json)).
   Puis `fetch_mbids` → `score_vivier` → plaques / ranking.
2. **Quotas fantasy sur le draft** — planchers `basse` / `batterie`, plafond `voix`
   (voir [`tools/draft_serie1.py`](../tools/draft_serie1.py) et
   `fantasy_instrument_quotas`).
3. **Score relatif par poste** — ci-dessus.
4. Optionnel si le pool reste tendu : léger biais de drop booster commune/argent
   vers `basse` / `batterie` (économie, pas scoring).

## Hors V1

- Remplaçants / wild card.
- Bonus synergie de vrai groupe (sceau).
- Cap platine additionnel.

## Proto

- Lobby → [`prototypes/fantasy.html`](../prototypes/fantasy.html)
- Verrou marché branché dans [`prototypes/booster.html`](../prototypes/booster.html)
  via `freeCopiesFor` (lineup compte comme réservation).
