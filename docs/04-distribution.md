# Distribution des cartes

## Boosters

- **5 cartes par booster.**
- **1 booster gratuit par jour**, complété par des quêtes et des mini-jeux.
- Aucun booster achetable en argent réel (voir `01-cadre-juridique.md`).

### Structure à slots

Cinq cartes, une seule carte « haute » (elle remplace l'or) :

| Cartes | Contenu |
|---|---|
| 1 haute | Or 75 % · Platine 20 % · Diamant 5 % |
| 1 ou 2 | Argent (une chance sur deux d'en avoir deux) |
| le reste | Commune |

Soit **25 %** de chance d'une platine ou mieux par booster, une diamant toutes les
~20 ouvertures. Plus de palier légendaire : les 40 cartes qui l'étaient sont des diamants
(48 au total), pour que le palier reste long à 5 %.

### Pity timer

Indispensable, et désormais un standard — voire une obligation de transparence dans
certaines juridictions.

- Diamant garantie dans les **10 premiers boosters** d'un nouveau joueur.
- Puis diamant garantie au plus tard toutes les **40 ouvertures**.
- Platine garantie au plus tard toutes les **20 ouvertures** (un diamant reset aussi ce compteur).

**Les taux doivent être publiés** sur une page accessible.

## Volumétrie des paliers

Sur une Série 1 de 2 000 cartes. Le produit `taux × taille du palier` détermine le taux
de doublons et la durée de complétion, donc la liquidité du marché.

| Palier | Cartes | Part |
|---|---:|---:|
| Commune | 1 022 | 51,1 % |
| Argent | 560 | 28 % |
| Or | 260 | 13 % |
| Platine | 110 | 5,5 % |
| Diamant | 48 | 2,4 % |

Les paliers sont attribués par **rang centile** dans la série, jamais par seuil absolu.

## Taille de la Série 1

**2 000 artistes**, mélange 80 icônes / 400 connus / 900 scène / 600 deep cuts.
Construction détaillée dans [`08-serie-1.md`](08-serie-1.md).

Repère : 5 cartes par jour font 1 825 cartes par an. Un set de 2 000 cartes représente
donc déjà plus d'un an de collection pour un joueur purement gratuit.

## Synergie de groupe

Puisqu'il n'y a pas de carte « groupe », réunir tous les membres d'un groupe active un
**set bonus**.

C'est ce que la règle « une carte par personne » rend possible, et ça transforme la
contrainte en atout : le batteur commun devient un objet de chasse, ce qui donne de la
liquidité au marché sur les cartes de bas palier.

Le **sceau de groupe** (voir `05-direction-artistique.md`) rend cette synergie lisible
à l'œil.

## Doublons et puits d'inflation

> Détaillé dans la brique 2, listé ici parce que c'est indissociable de la distribution.

- **Destruction de doublons** : convertit un exemplaire en crédits (puits + liquidité).
  Pas de craft : le marché fixe le prix des manquantes.
- **Taxe de transaction de 5 à 10 %** sur le marché, qui détruit de la monnaie.
- **Cooldown anti-bot** sur les comptes neufs, plafonds d'échange, aucune passerelle
  vers l'argent réel.
