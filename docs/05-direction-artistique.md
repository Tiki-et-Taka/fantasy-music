# Direction artistique

Principe fondateur : **on ne dessine pas la personne, on dessine l'interprète.**
Un batteur de dos en plein coup, un trompettiste à contre-jour, un chanteur dont les
cheveux masquent le visage. C'est figuratif, humain, chargé en émotion, et ça ne
représente juridiquement personne.

Illustrations de référence dans [`../references/`](../references/).

## Les trois styles retenus

| Style | Caractère | Référence |
|---|---|---|
| **Sérigraphie** | Affiche de concert, aplats d'encre, trame de demi-teintes, palette limitée à trois couleurs. Se lit instantanément même en vignette de 80 px. | `references/direction-serigraphie.jpg` |
| **Contre-jour** | Silhouette entièrement à contre-jour dans une brume de lumière de scène. Élégant, intemporel ; le visage est masqué par le dispositif lui-même. | `references/direction-contrejour.jpg` |
| **Encre et lavis** | Pinceau expressif, contraste brutal, projections d'encre. Magnifique mais lourd à grande échelle, et illisible en petit. | `references/direction-encre.jpg` |

*Écartée : la ligne claire vectorielle — la moins chère mais la moins chargée
émotionnellement.*

## Escalade de style par rareté

Deux paliers par style, avec un second axe d'escalade : **la fenêtre d'illustration
grignote le bandeau typographique à chaque cran.** En Commune, le dessin est dans une
vignette avec un large bandeau de texte en dessous ; en Mythique, l'illustration occupe
toute la carte et le texte se pose dessus. C'est la convention des séries « borderless »
de Magic : l'œil perçoit la rareté avant de lire le libellé.

| Palier | Style | Exécution |
|---|---|---|
| Commune | Sérigraphie | 2 encres, trame grossière, plan large |
| Peu commune | Sérigraphie | 3 encres, trame fine, plan resserré |
| Rare | Contre-jour | Halo unique, arrière-plan sobre |
| Épique | Contre-jour | Fumée, second plan, reflets de scène |
| Légendaire | Encre et lavis | Lavis assemblé, palette restreinte |
| Mythique | Encre et lavis | Pièce unique, rehauts, pleine carte |

La rareté se lit à l'épaisseur et à la complexité du cadre — filet simple, double filet,
équerres d'angle, bandeaux, hachure holographique — **pas à la couleur du fond**, qui
reste réservée au genre. Cela évite l'effet arc-en-ciel.

## Les sept couches de composition

Chaque carte est assemblée automatiquement. Aucune couche n'est décidée à la main.

| Couche | Donnée qui la pilote | Source | Variantes |
|---|---|---|---|
| Style et exécution | Palier de rareté | Score composite | 3 styles × 2 exécutions |
| Pose et cadrage | Instrument principal | `P1303` → 8 familles | ≈ 56 poses |
| Costume et silhouette | Décennie de début de carrière | `P2031`, `P569`, 1re sortie MusicBrainz | 5 tranches |
| Palette | Genre canonique | `P136` → 20 familles racines | 20 palettes |
| Décor et échelle de scène | Rang centile de notoriété | Score composite | 5 lieux |
| Traitement lumineux | Palier de rareté | Score composite | 6 niveaux |
| Sceau de groupe | Groupe principal | `P463` / MusicBrainz | hash |

Le décor est le plus narratif des sept : du petit club enfumé au stade, **le lieu reflète
la notoriété**, ce qui rend la rareté racontée et pas seulement décorative.

## Sceau de groupe

Une rosace **générée, jamais dessinée** : le nom du groupe est haché, et le hash choisit
un anneau, un polygone étoilé, un cœur et un nombre de graduations. Trente lignes de
code, zéro octet stocké, réponse instantanée pour n'importe quel groupe.

Le même sceau apparaît sur les cartes de tous les membres d'un groupe, ce qui rend le
bonus de synergie lisible à l'œil.

**Contrainte mathématique :** le polygone étoilé `{n/k}` dégénère en simple trait si
`gcd(n, k) ≠ 1` ou si `k ≥ n/2`. Il faut filtrer les valeurs valides.

**Espace de formes :** quatre axes indépendants donnent environ 960 formes distinctes.
C'est suffisant parce que le sceau est une **aide à la reconnaissance, pas un
identifiant** — le nom du groupe est imprimé juste à côté, et une Série 1 de 2 000
artistes ne génère qu'environ 300 à 400 groupes distincts. Pour monter à plusieurs
milliers, ajouter une rotation discrète et un motif de brisure sur l'anneau.

## Table de mapping des genres

Vingt familles racines, chacune avec un fond sombre et deux accents. La colonne
**Prio.** est le rang de départage quand un artiste retombe dans plusieurs familles.

| Famille | Fond | Accent 1 | Accent 2 | Prio. | Genres Wikidata qui y retombent |
|---|---|---|---|---:|---|
| Métal | `#121214` | `#B8352F` | `#6E7276` | 1 | heavy metal, death metal, metal progressif, metal industriel, black metal |
| Punk & hardcore | `#141416` | `#E04A2F` | `#F0E9D8` | 2 | punk rock, hardcore punk, post-punk, oi!, crust |
| Hip-hop | `#121410` | `#C8D44E` | `#6E7A52` | 3 | rap, gangsta rap, boom bap, trap, drill, rap conscient |
| Électronique | `#0B1220` | `#3FC1C9` | `#7A86D6` | 4 | techno, house, drum and bass, ambient, IDM, EBM |
| Reggae & dub | `#0F1610` | `#D9B52B` | `#4E9B5A` | 5 | reggae, dub, ska, rocksteady, dancehall, ragga |
| Afro | `#16120C` | `#E09A2B` | `#4F8C6E` | 6 | afrobeat, afropop, highlife, mbalax, amapiano, soukous |
| Latin | `#1C1210` | `#D4552F` | `#E0A83C` | 7 | salsa, bossa nova, cumbia, tango, reggaeton, samba |
| Jazz | `#0E1A1C` | `#D8B35C` | `#6FA3A0` | 8 | bebop, cool jazz, free jazz, jazz modal, swing, hard bop |
| Blues | `#0C1420` | `#4A7FB5` | `#C4A062` | 9 | delta blues, chicago blues, blues rock, boogie-woogie |
| Gospel & sacré | `#120F16` | `#D8C06A` | `#8A7AB0` | 10 | gospel, negro spiritual, musique liturgique, qawwali |
| Funk & disco | `#1A1222` | `#E0A32B` | `#C04FA8` | 11 | funk, disco, p-funk, boogie, funk rock |
| R&B & soul | `#1A1012` | `#C47A5A` | `#8E6B8C` | 12 | soul, rhythm and blues, motown, neo soul, contemporary R&B |
| Country | `#171310` | `#C89A4A` | `#8C6E4E` | 13 | country, bluegrass, honky-tonk, americana, outlaw country |
| Folk | `#121710` | `#9CB06A` | `#C4A878` | 14 | folk, singer-songwriter, folk rock, néo-folk, protest song |
| Classique | `#14110C` | `#C9B07A` | `#7E8A7A` | 15 | musique baroque, romantisme, opéra, minimalisme, musique de film |
| Musiques du monde | `#101614` | `#B58A4E` | `#5E8C86` | 16 | musique traditionnelle, fado, flamenco, raï, musique celtique |
| Chanson & variété | `#16131A` | `#C9869B` | `#A08C5E` | 17 | chanson française, schlager, canzone, variété, yé-yé |
| Expérimental | `#111113` | `#A8AEB4` | `#D8D2C2` | 18 | musique concrète, noise, drone, avant-garde, musique sérielle |
| Pop | `#1C1020` | `#D45E8A` | `#E0B36A` | 19 | pop, synthpop, dream pop, J-pop, K-pop, teen pop |
| Rock | `#15110E` | `#D98A2B` | `#8A6A4F` | 20 | rock, rock alternatif, rock progressif, indie rock, grunge, garage |

### Pourquoi Pop et Rock sont en dernier

Ce sont les familles **parapluie** de Wikidata, attachées à presque tout le monde.
Dream Theater porte « rock progressif » en plus de « metal progressif » ; Marilyn Manson
porte « rock alternatif » en plus de « metal industriel ». Un vote majoritaire ferait
virer la moitié du catalogue au brun-ambre. En classant par spécificité décroissante,
le métal l'emporte sur le rock et le hip-hop sur la pop.

### Algorithme de résolution

| Étape | Traitement | Pourquoi |
|---|---|---|
| 1. Collecte | Tous les `P136` de l'artiste | Wikidata en donne typiquement 3 à 6, non ordonnés |
| 2. Remontée | Parcours des `P279` jusqu'à une famille racine, profondeur max 6 | Le graphe des genres contient des cycles |
| 3. Départage | La famille de plus haute priorité l'emporte | Évite que tout converge vers Rock ou Pop |
| 4. Cohérence | **La famille du groupe écrase celle du membre** | Deux membres du même groupe doivent partager la palette |
| 5. Repli | Groupe → tags MusicBrainz → label → Expérimental | Couvre les fiches incomplètes |

La résolution se fait **hors ligne, une fois** : Wikidata ne compte qu'environ 2 500
genres musicaux, d'où un dictionnaire `genre → famille` que le jeu consulte en mémoire.

### Les deux endroits qui demandent du travail manuel

1. **Table d'override pour les 200 genres les plus fréquents.** Le graphe `P279` est
   irrégulier ; c'est là que se joue l'essentiel de la qualité perçue. Quelques heures,
   une seule fois.
2. **Les genres à double appartenance** — jazz fusion, rap rock, country rock, folk
   metal, blues rock. À trancher à la main une bonne fois.

## Volumétrie et coût de production

Le style le plus cher ne couvre que les paliers les plus rares : c'est cet alignement
qui rend le système finançable.

| Palier | Cartes | Style | Mode de production | Coût |
|---|---:|---|---|---:|
| Commune | ≈ 1 020 | Sérigraphie 2 encres | Assemblage automatique | 0 € |
| Peu commune | ≈ 560 | Sérigraphie 3 encres | Assemblage automatique | 0 € |
| Rare | ≈ 260 | Contre-jour | Assemblage automatique | 0 € |
| Épique | ≈ 110 | Contre-jour enrichi | Assemblage + retouche | faible |
| Légendaire | ≈ 40 | Encre assemblée | Bibliothèque de ≈ 20 lavis | 2 000 – 4 000 € |
| Mythique | ≈ 8 | Encre, pièce unique | Commande à l'illustrateur | 2 400 – 4 000 € |

**97 % du catalogue ne coûte rien à illustrer.** Budget total estimé entre 5 000 et
8 000 €, concentré là où le joueur le verra.

### Remplir la bibliothèque

- **Commande à un illustrateur** : meilleur résultat, cohérence parfaite, mais
  60 illustrations à 80–200 € pièce mettent entre 5 000 et 12 000 €.
- **Génération IA curée à la main** : coût quasi nul, mais deux réserves. Une œuvre
  purement générée par IA n'est pas protégeable aux États-Unis (impact pratique faible).
  Surtout, **les communautés de fans de musique sont souvent hostiles à l'art généré**,
  et c'est précisément le public visé.
- **Arbitrage retenu** : corpus de base généré puis **retouché et unifié par un
  illustrateur** (quelques jours), avec les cartes de haut palier dessinées entièrement
  à la main. On paie là où ça se voit.

## Assets gratuits et vraiment libres

| Ressource | Licence |
|---|---|
| Game-icons.net — 4 000+ icônes pensées pour les jeux | CC BY 3.0 |
| Lucide, Phosphor | MIT |
| Google Fonts, Fontshare | SIL OFL |
| Poly Haven, ambientCG, Kenney.nl — textures | CC0 |
| Figma, Inkscape, Krita, Blender — outils | libres |

⚠ Beaucoup de polices « metal » ou gothiques trouvées en ligne ne sont **pas** libres
pour un usage commercial. Vérifier systématiquement.

## Pipeline de rendu

Composer en SVG ou HTML/CSS, pré-rendre en WebP/AVIF via `satori` + `resvg` dans un job
batch, stocker sur Cloudflare R2 derrière le CDN. **Aucune génération d'image à la volée
en production.**
