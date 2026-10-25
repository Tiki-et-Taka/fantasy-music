# Marché — prix fixe (brique 2)

Décision : **annonces à prix fixe** en crédits. Pas d’enchères au lancement.

## Règles

| Règle | Valeur |
|---|---|
| Unité | 1 exemplaire d’une carte (`card_id`) |
| Prix | Entier libre ≥ **1** crédit |
| Taxe | **10 % arrondie** (`round`), détruite — donc &lt;5 → 0, 5–14 → 1, 15–24 → 2, etc. |
| Vendeur reçoit | Prix − taxe (toujours entier) |
| Mise en vente | La carte **reste dans le classeur** avec un badge « en cours de vente » (exemplaire réservé) |
| Annulation | Gratuit — l’annonce disparaît, le badge aussi |
| Achat | Paiement immédiat du prix affiché |
| Filtre | **Toutes** · **Mes ventes** · **Offres reçues** · **Offres envoyées** |
| Contre-offre | Prix libre &lt; prix affiché ; cloche → menu notifs (« Offre reçue de… ») → **Offres reçues** ; badge **Offre !** |
| Côté vendeur | Offres listées dans **Offres reçues** (crédits + échanges ; accepter ou refuser) |
| Offres reçues | Contre-offres crédits + échanges reçus sur tes annonces ; badge **Offre !** |
| Offres envoyées | Échanges proposés + contre-offres crédits que tu as envoyées |
| Contre-offre | **Crédits** (prix &lt; affiché) ou **échange** de carte (même rareté, annonces joueur) via le même bouton Contre-offre |
| Échange P2P | Contre-offre → Proposer un échange → ta carte libre ; notif vendeur → **Offres reçues** ; notif initiateur → **Offres envoyées** |

Pas de craft : les manquantes s’obtiennent en booster ou sur le marché.
Repère bas de prix (proto) : crédits rendus à la destruction d’un doublon.

## Hors scope (plus tard)

- Enchères anglaises, paniers multi-cartes.
- Historique public des ventes (utile pour l’anti-bot / la cote).
- Plafonds pour comptes neufs (anti-bot) — à brancher avec les comptes serveur.

## Prototype

Onglet **Marché** dans [`prototypes/booster.html`](../prototypes/booster.html) :
annonces joueur + stock PNJ de démonstration (localStorage `charts.s1.market`).
