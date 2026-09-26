# 01 — Analyse de structure : tarif Evolis CISMEA (AUG2026 A0)

> Livrable de la phase 1. Aucune ligne de code applicatif n'a été écrite.
> Les chiffres viennent de sondes d'analyse (`tools/analysis/`) lancées sur le PDF ;
> le parser de la phase 2 les recalculera et les contrôlera.
> **Aucun prix n'est reproduit dans ce document** : le dépôt est public.

## 1. Méthode

- Rendu des 34 pages en PNG à 150 dpi (PyMuPDF) et relecture visuelle de chacune ; zooms à 300 dpi sur les cas douteux.
- Dumps pdfplumber des pages 4, 26 et 30 : mots et caractères avec coordonnées, police, taille, couleurs ; rectangles et courbes.
- Sondes sur tout le document : grille des tableaux, affectation des caractères aux cellules, flags, notes, doublons, matrice (colonnes, coches, renvois) et résolution des codes.
- Confrontation aux valeurs golden du cahier des charges (§7).

## 2. Carte du document

| Pages | Format | Contenu |
|---|---|---|
| 1 | A4 portrait | Couverture : « CISMEA - EURO », « Prices in EURO (€) - Effective from August 18th, 2026. », référence « Price_list-CISMEA-EURO AUG2026 A0 » |
| 2 | A4 portrait | Sommaire (famille → page) et légende « N: New product / I: Price Increase / D: Price Decrease » |
| 3–29 | A4 portrait, 595 × 842 pt | Tarif : 14 familles, 59 tableaux |
| 30–34 | A3 paysage, 1190 × 842 pt | Matrice de compatibilité, document distinct « KB-EHT1-1037-ENG-A3-D2 » |

Le PDF 1.6 a été produit par « Acrobat PDFMaker 26 pour Excel » (créé le 30/07/2026, modifié le 19/08/2026). Il n'est pas chiffré.

**Le tarif est un export Excel.** On a donc une grille vectorielle régulière et une couche texte propre (police Montserrat) : aucune OCR n'est nécessaire. Revers de la médaille : les cellules se comportent comme des cellules Excel, avec du texte parfois rogné ou débordant (§4.13).

Familles (titre rouge de 16,32 pt), conformes au sommaire de la p.2 :

| Famille | Pages | Contextes (lignes-produits) |
|---|---|---|
| BADGY | 3 | 13 |
| ZENIUS | 4–5 | 46 |
| ZENIUS 2 | 6–7 | 47 |
| PRIMACY & PRIMACY LAMINATION | 8–9 | 55 |
| PRIMACY 2 | 10–13 | 98 |
| GO PACK BUNDLES | 14 | 4 |
| AVANSIA | 15–16 | 31 |
| AGILIA | 17–19 | 56 |
| QUANTUM 2 | 20–21 | 39 |
| TATTOO RW | 22 | 9 |
| SIGNATURE PADS | 23 | 8 |
| CARDPRESSO | 24 | 18 |
| ID-ALL | 25 | 20 |
| SUPPLIES & CONSUMMABLES (*sic*) | 26–29 | 149 |

Les pages sans titre de famille sont les p.5, 7, 9, 11–13, 16, 18–19, 21 et 27–29, exactement la liste du cahier des charges.

## 3. Signature typographique, base de la classification

Chaque élément se reconnaît au triplet police, taille et couleur. C'est plus robuste que la position, qui varie d'une page à l'autre.

| Élément | Police | Taille (pt) | Couleur (RVB 0–1) |
|---|---|---|---|
| Titre de famille | Montserrat-Regular | 16,32 | rouge (0,863 ; 0 ; 0,078) |
| Titre de section | Montserrat-Regular | 8,88 ou 9,6 | rouge (0,859 ; 0 ; 0,106) |
| Libellés d'en-tête de tableau | Montserrat-SemiBold | 7,44 | bleu nuit (0,137 ; 0,255 ; 0,392), sur bandeau gris (0,902) |
| Texte des cellules | Montserrat-Regular | 7,44 | noir |
| Flag N/I/D | Montserrat-Regular | 7,44, ou 8,16 (p.22 et 26–29) | rouge (0,863 ; 0 ; 0,078), dans la marge gauche |
| Note sous un tableau (« * … », « (1) … ») | Montserrat-Italic | 7,44 | noir |
| En-tête de page « PRICE LIST - CISMEA / EURO » | Montserrat-SemiBold | 8,88 | bleu nuit |
| « Prices in EURO (€) - Effective from … » | Montserrat-Regular | 7,44 | noir |
| Pied « ©2026 Evolis… » et n° de page | Montserrat-Regular | 8,04 | bleu nuit |
| Coches de la matrice | Wingdings2, glyphe U+F050 | 15,36 | bleu nuit |

Caractères non ASCII du document : © ® ’ € et U+F050 (les coches). **Il n'y a aucune espace insécable (U+00A0) ni espace fine (U+202F).** Le séparateur de milliers est partout l'espace ordinaire U+0020. Le parser acceptera quand même les trois variantes, en prévision des versions futures.

## 4. Tableaux de prix (p.3–29)

### 4.1 Détection

- Un tableau commence par une ligne d'en-tête « Product Code · Product Description · LIST PRICE », suivie de « · Standard Packaging Qty » sur les p.26–29. On en compte 59. L'en-tête « Standard / Packaging Qty » tient sur deux lignes.
- La hauteur du bandeau gris varie de 15,7 à 21 pt. Sur les p.20–22, le cadre extérieur englobe aussi l'en-tête. Une détection par la forme du bandeau échoue donc : la détection se fait **par les libellés**, comme le demande le cahier des charges.

### 4.2 Colonnes

- La grille est dessinée par des rectangles pleins de 0,72 pt (gris 0,749). pdfplumber ne renvoie aucune `lines`, uniquement des `rects`.
- Les bordures verticales donnent les limites exactes des colonnes, et les centres des libellés disent quelle colonne est laquelle.
- On relève **8 variantes de positions** : le bord gauche du tableau va de 32,4 à 52,0 pt et la colonne code mesure de 72,6 à 112,2 pt de large. Aucune coordonnée n'est donc codée en dur : tout est recalculé pour chaque tableau.

### 4.3 Lignes

- Chaque ligne est fermée par une règle horizontale. Les caractères sont affectés aux cellules selon **leur centre**.
- Sur les p.7, 11 et 17, des lignes de texte débordent sur la règle (756 caractères chevauchants). L'affectation par le centre les range quand même dans la bonne ligne : c'est vérifié sur les 593 lignes.
- Six lignes vides servent de séparateurs (4 en p.24, 2 en p.25). Elles sont ignorées sans anomalie.

### 4.4 Codes

- 329 codes uniques, tous conformes à `[A-Z0-9]+(-[A-Z0-9]+)*`, de 5 à 20 caractères. Même en ajoutant les 17 codes hors tarif (§5.6), la normalisation (majuscules, sans séparateurs) ne crée aucune collision.
- **5 codes sont coupés sur deux lignes dans leur cellule** : QTM306GRH-/BS000-MB1 et QTM306GRH-/BS00K (p.20), ST-BE105-2-UEVL-/MB1, ST-CE1075-2-UEVL-/MB1 et ST-GERT-3-UEVL-/MB1 (p.23). Règle : une ligne terminée par « - » collé à un mot se concatène sans espace. Le même phénomène touche les descriptions (« with ID- / ALL Starter » en p.10, 11 et 17).
- Deux codes portent un astérisque de renvoi collé : CBGR0500F* et CBGCP030W* (p.3). On stocke le code sans l'astérisque et on le lie à la note « * Paper Cards compatible with Badgy Solutions from S/N 10001082236 ». Ces deux codes réapparaissent sans astérisque en p.27 et p.29.
- La couche texte tranche les confusions visuelles de Montserrat entre O et 0, I et 1. Exemples : ZN1H0OMNRS contient un zéro puis un O ; QTM2-OPxxx et QTM2-KTOMN contiennent la lettre O.

### 4.5 Prix

- 589 prix entiers, sans aucune décimale dans ce tarif, avec le séparateur U+0020. Ils seront stockés en centimes.
- 4 prix sont sur demande, notés « (1) » : S-CP1000, S-CP1000AC, S-CP1000EL (p.24) et IDALL-E1 (p.25). Chacun renvoie à une note en italique sous le tableau.

### 4.6 Conditionnement (p.26–29)

149 lignes portent un conditionnement standard. Les valeurs sont 1, 5, 6, 10, 12, 16, 20 et 28.

### 4.7 Flags

- La marge gauche porte 438 glyphes rouges, soit exactement 438 lignes flaguées, **sans aucun orphelin**. Leur abscisse varie de 13 à 39 pt selon la page : le repérage se fait par rapport au bord gauche du tableau, et verticalement par la bande de la ligne.
- On compte **436 « I » et 2 « N »** (R2F226NAAA, p.12 et p.27). **Aucun « D »** dans cette édition, bien que la légende le prévoie.
- Trois codes changent de flag selon le contexte :
  - S10149 : sans flag p.5, « I » p.7, 9, 13 et 29 ;
  - A5070 : sans flag p.13, « I » p.9, 16, 19 et 29 ;
  - R6F003SAA : « I » p.8, sans flag p.27.

  On stocke donc le flag par contexte, avec un flag agrégé au niveau de l'article et une anomalie non bloquante.

### 4.8 Hiérarchie

- On relève 24 intitulés de section distincts. S'ajoutent à ceux du cahier des charges :
  - WARRANTY EXTENSION au singulier (p.7) ;
  - CLEANING (p.19) ;
  - OPTIONS FIELD UPGRADABLE (p.21) ;
  - SOFTWARE (p.23) ;
  - SIGNATURE PADS, section homonyme de la famille ;
  - CARDPRESSO EDITION et CARDPRESSO UPGRADES ;
  - ID-ALL EDITION et ID-ALL UPGRADES ;
  - CARD PRINTING SOLUTION, sans simplex ni duplex (p.15 et 20).
- **La section se propage aussi d'une page à l'autre.** Le premier tableau de la p.27 n'a pas de titre : il continue « DIRECT-TO-CARD COLOR RIBBONS » de la p.26.
- La source est incohérente pour le pack Primacy 2 LED Duplex (PM2D-GP3-M) : il est rangé sous « … - SIMPLEX PRINTERS », seule section de la p.14. Le recto-verso se déduit donc de la désignation, pas de la section.

### 4.9 Descriptions sur plusieurs lignes

- En principe, la première ligne donne le nom commercial et les suivantes les détails. Mais Excel mélange deux cas :
  - des **sauts de ligne explicites** : listes « - … », lignes « 1 x … », notes ;
  - des **retours à la ligne automatiques**, pour les phrases trop longues.
- Pour les distinguer, on applique une règle géométrique : si le premier mot de la ligne suivante tenait dans la place restante, le saut était explicite ; sinon, c'est un retour automatique. Sur 324 transitions, on obtient 205 sauts et 119 retours. Quelques cas restent limites, par exemple « 400 prints / roll » des rubans RT.
- Les lignes brutes sont conservées avec leur bbox : la reconstitution sert à l'affichage, jamais à produire une valeur.
- Six codes ont une description différente selon le contexte :
  - R6F207NAAA porte « (Supported on Zenius 2 Expert only) » dans le seul contexte ZENIUS 2 ;
  - LPS070NAA, LPS071NAA, LPA072NAA, LPA073NAA et LPA074NAA portent « Not recommended for PVC Cards » dans le seul contexte AGILIA.

  Ces mentions sont donc des **conditions liées au contexte**, pas des propriétés de l'article.

### 4.10 Notes embarquées → relations et attributs

| Texte source | Codes | Traitement |
|---|---|---|
| « (To finalize the installation, it is necessary to order the encoder's mounting plate: S10112) » | S10281, S10170, S10169, S10919 (Zenius, Zenius 2, Primacy, Primacy 2) et S10921 (Agilia) : 14 contextes | requires → S10112 |
| même phrase, « …: S10465 » | S10459, S10463 (Agilia) | requires → S10465 |
| « For Stand Alone use, order USB cable (ref A5017) » | S10212 (p.9, 13) | requires → A5017, sous condition « usage autonome » |
| « ( minimum order quantity is 4) » | PMY1-KTDS, PMY2-KTDS | moq = 4 |
| « To be installed by an ERC (Evolis Repair Center) partner » | S10386, S10177 | install_by_partner = ERC |
| « (contact us for availability) » | LPS071NAA, LPA072NAA à LPA074NAA : 12 contextes | availability_on_request. Souvent coupé sur deux lignes : la détection se fait sur le texte joint |
| « Not recommended for PVC Cards » | 5 codes, dans le contexte AGILIA | restriction liée au contexte |
| « (Supported on Zenius 2 Expert only) » | R6F207NAAA, dans le contexte ZENIUS 2 | restriction liée au contexte |
| « * Paper Cards compatible with Badgy Solutions from S/N 10001082236 » | CBGR0500F*, CBGCP030W* | min_serial (Badgy) |
| « (1) The XXS edition … » / « (1) The ID-ALL Starter edition is submitted to prices per quantity… » | les 4 codes sur demande | on_request, avec la note liée |

Deux incohérences viennent de la source, pas du parser :

- S10921 (Agilia) renvoie à la plaque S10112, alors que les autres kits Agilia renvoient à S10465 ;
- S10458 (Agilia) ne mentionne aucune plaque.

Elles donneront des anomalies « à vérifier auprès d'Evolis », non bloquantes, sans aucune correction automatique.

### 4.11 Bundles

| Bundle | Composants dans le PDF | Résolution possible sans deviner |
|---|---|---|
| QTM306GRH-BS000-MB1 | Codes cités : QTM306GRH-BS, QTM3-KT001, QTM3-KT002 | Complète ; la somme des composants est conforme à la valeur golden |
| ST-BE105-2-UEVL-MB1, ST-CE1075-2-UEVL-MB1, ST-GERT-3-UEVL-MB1 | « includes 1xSig100 + 1 CD-ROM with signoSign/2 and 1 licence… » | Base = code sans « -MB1 », qui existe dans le tarif. La licence correspond à L8500 par son libellé : à confirmer |
| GO PACK : ZN1U-GP1, ZN2-GP-M, PM2S-GP2-M, PM2D-GP3-M | Lignes « 1 x … » en texte libre, sans aucun code | Partielle. « Zenius Classic Fire Red » est le nom exact de ZN1U0000RS, « Zenius 2 Classic » celui de ZN2-0001-M. « YMCKO ribbon for 200 prints » est ambigu (R5F002EAA, R5F002SAA ou R5F202M100). « cardPresso XS Edition » et « ID-ALL Standard Edition » sont absents du tarif |
| B22U0000RS (Badgy200 « Card printing solution ») | Puces « - Badgy200 plastic card printer… » | Composants en texte libre ; l'imprimante seule n'est pas au tarif |
| CBGP0001C (pack de consommables) | « 1 YMCKO color ribbon for 100 prints + 100 blank PVC WHITE cards… » | Candidats CBGR0100C et CBGC0030W : à confirmer |

Niveaux de résolution proposés, du plus sûr au moins sûr :

1. `cited` : le code est écrit dans le texte ;
2. `suffix` : suffixe « -MB1 » retiré ;
3. `name_exact` : nom identique ;
4. `name_tokens` : mêmes mots dans un autre ordre ;
5. `override` : confirmation manuelle ;
6. `ambiguous` ou `unresolved`.

Seuls `cited` et `suffix` sont appliqués automatiquement ; les autres restent « à confirmer » dans le rapport. La somme des composants n'est calculée que si tous sont résolus.

### 4.12 Bruit à filtrer

Le bruit comprend :

- l'en-tête de page : logo, « PRICE LIST - CISMEA / EURO », « Prices in EURO… » ;
- le pied de page : « ©2026 Evolis… » et numéro de page ;
- les images : logo et photo produit ;
- les arcs décoratifs, sous forme de courbes vectorielles.

Tout cela est hors des tableaux et donc exclu par construction : seuls sont lus le contenu des cellules, les titres, les flags et les notes en italique.

### 4.13 Pièges de l'export Excel

- **Texte rogné.** La description de PM2-0042 s'arrête sur « …with ID-ALL Starter Edition software ». Le mot suivant n'existe pas dans le PDF (vérifié dans la couche texte et sur un rendu à 300 dpi). On stocke le texte tel quel, avec une anomalie de niveau info « texte possiblement tronqué ».
- **Texte qui déborde de la cellule** (p.7, 11, 17) : réglé par l'affectation selon le centre des caractères.
- **Coquilles de la source**, conservées telles quelles : « CONSUMMABLES », « Retranfer », « with with », « contacless », « daugther ». La recherche floue sur les mots de 5 lettres ou plus les absorbe.

## 5. Matrice de compatibilité (p.30–34)

### 5.1 Structure

- La matrice compte 8 blocs. Chaque bloc a un bandeau d'en-tête gris, une barre de section bleu nuit à texte blanc, puis des lignes séparées par des règles noires de 0,6 pt.
- Les 8 sections sont : CONSUMABLE PACKS, DIRECT-TO-CARD COLOR RIBBONS, DIRECT-TO-CARD MONOCHROME RIBBONS, RETRANSFER FILMS & RIBBONS, SECURITY RIBBONS, ACCESSORIES, CLEANING KITS et CARDS.
- Les colonnes fixes sont Product Code (en rouge), Description et Prints / Roll, suivies des 19 colonnes imprimantes. La colonne Prints / Roll contient aussi du texte, comme « 5 adhesive cards, 5 swabs » ou « 1 pack of 500 cards » : elle est conservée brute.
- **160 lignes au total.** La dernière ligne d'un bloc peut ne pas avoir de règle inférieure (S10277, p.33) : on la ferme sur l'en-tête suivant.

### 5.2 Colonnes et groupes

- On retrouve à l'identique les 19 colonnes du cahier des charges sur les 8 blocs. Les libellés sur plusieurs lignes sont regroupés par leur centre. Attention : « Quantum2 » et « Tattoo2 RW » ne sont séparés que de 7,5 pt.
- Certains libellés contiennent des codes : « Primacy2 + CLM (S10212, S10252) », « Avansia + CLM (S10293) », « Agilia + CLM (S10474) », « Primacy Lamination (S10212, S10252) ». On en tire le modèle d'imprimante et le module requis, lié aux articles correspondants.
- Les groupes sont BADGY, ID RANGE, RETRANSFER RANGE, EDIKIO et DISCONTINUED. CATALOGUE est un super-groupe qui réunit tout ce qui n'est pas discontinué.
- Les libellés de groupe sont centrés sur leurs colonnes, sans bornes dessinées. On en déduit la partition contiguë optimale par programmation dynamique. Le résultat est le même sur les 8 blocs, y compris en p.32 où « RETRANSFER RANGE » est décalé de 21 pt. Un séparateur vertical blanc (x ≈ 946 pt) confirme la frontière avec DISCONTINUED.
- EDIKIO (Access, Flex, Duplex) n'a pas de famille dans ce tarif. À l'inverse, PRIMACY et PRIMACY LAMINATION sont marqués discontinués dans la matrice, alors que leurs consommables et options sont vendus en p.8–9. La correspondance entre familles et modèles passera donc par un fichier de configuration validé par vous (voir 03, décision D6). L'import signalera toute famille non reliée.

### 5.3 Coches

- On compte 558 glyphes Wingdings2 U+F050. Chacun est affecté à la colonne dont le centre de libellé est le plus proche.
- **L'écart maximal est de 2,7 pt pour un pas de 41,9 pt** : aucune ambiguïté sur cette édition.
- Garde-fou : un écart supérieur à 25 % du pas déclenchera une anomalie et l'analyse du rendu image de la cellule. Ce secours n'est pas nécessaire ici.

### 5.4 Renvois et numéros de série

- Des marqueurs « (1) » à « (4) » (3,96 pt) sont placés à droite de certaines coches ; on les rattache à la coche de gauche. Cela concerne 16 cellules. Les notes correspondantes sont :
  - (1) CR80 white cards only (p.30, 31) ;
  - (2) Zenius 2 Expert only ;
  - (3) Not recommended for PVC cards ;
  - (4) 100 cards standard hopper only.
- Le marqueur d'une note de bas de page n'a parfois pas la même taille que son texte : on les regroupe par ligne de base.
- 8 cellules portent « From S/N: … » **sans coche**, sur deux lignes en 4,2 pt :
  - C2501, C2511, C4521, C7001 et C8521 pour Access ;
  - C4003 pour Agilia et Agilia + CLM ;
  - CBGCP030W pour Badgy100 & 200.

  On les enregistre comme compatibilités avec un numéro de série minimal (min_serial).

### 5.5 Codes génériques

La matrice contient 16 motifs génériques, comme `R5F002xxx`, `R5F202xxxx` ou `RT4F010xxx`. On les résout par préfixe et longueur exacte : tous sont résolus, vers 21 codes du tarif. Cinq motifs couvrent chacun deux codes (variantes EAA et SAA) : R5F002, R5F008, R6F003, RT4F010 et RT5F011.

### 5.6 Codes hors tarif (17)

VBDG205EU, VBDG204EU, RCT025NAA, RCT052NAA, RCT081NAA, RCT094NAA, RCT095NAA, R4F226NAAA, S10277, A5024, A5021, C3501 (rPETG), C4152, C4122, C7001 (PLA/bois), C8152 et C8122.

Ils deviennent des articles « hors tarif » : compatibilité connue, prix inconnu. À noter : le rPETG et le PLA/bois n'existent que dans la matrice, pas dans le tarif.

### 5.7 Anomalies relevées dans la matrice

- **R4F226NAAA** (matrice, « SO (Silver, Overlay) », 600 impressions) contre **R2F226NAAA** (tarif, même désignation, flag N). Un seul caractère d'écart : probable coquille dans l'un des deux documents. En l'état, R2F226NAAA n'a aucune compatibilité. Pas de fusion automatique : le rapport proposera l'alias, à confirmer.
- **S10277** (DUST COVER) : ligne sans aucune compatibilité.
- **RTCT107NAAA** : coché pour « Agilia + CLM » mais pas pour « Agilia ». C'est le seul cas asymétrique, à vérifier.
- Coquilles : « PEN CEANING KIT » (ACL005) et « COMPOSITE PETF » (C3001).
- Couverture : tous les consommables et accessoires du tarif ont une ligne dans la matrice, sauf A5017 (câble USB) et R2F226NAAA (voir ci-dessus).

## 6. Anomalies attendues au premier import (aperçu du futur rapport)

| Gravité | Nature | Cas sur ce PDF |
|---|---|---|
| Bloquante | Ligne sans prix ni « (1) », code hors regex, prix divergents entre contextes, page de tarif à 0 ligne, écart de réconciliation, coche non affectable, colonnes de matrice différentes de l'attendu | **aucun** |
| Avertissement | Flag différent selon le contexte | S10149, A5070, R6F003SAA |
| Avertissement | Code de matrice proche d'un code du tarif | R4F226NAAA ↔ R2F226NAAA |
| Avertissement | Compatibilité asymétrique, ou ligne sans compatibilité | RTCT107NAAA ; S10277 |
| Avertissement | Composant de bundle ambigu ou non résolu | les 4 GO PACK, B22U0000RS, CBGP0001C, licence signoSign |
| Avertissement | Relation incohérente avec la famille | S10921 → S10112 (Agilia) |
| Info | Description différente selon le contexte (condition liée au contexte) | 6 codes |
| Info | Article hors tarif | 17 codes |
| Info | Texte possiblement tronqué | PM2-0042 |
| Info | Consommable sans compatibilité | A5017, R2F226NAAA |

## 7. Valeurs golden

Tout ce que lit la sonde dans le PDF est **conforme** au cahier des charges :

- les 14 cas prix, flag, gamme et conditionnement ;
- la décomposition de QTM306GRH-BS000-MB1 ;
- la relation S10281 → S10112 et le MOQ de PMY1-KTDS ;
- les 4 cas de compatibilité ;
- les 2 équivalences.

Aucune valeur du cahier des charges n'est à corriger.

## 8. Comptages préliminaires (à confirmer par le parser)

- **593 contextes** (lignes-produits) sur 59 tableaux, et **329 codes uniques** : 325 avec prix, 4 sur demande. 187 codes n'apparaissent que dans un contexte, 142 dans plusieurs ; le maximum est A5003, présent dans 9 contextes.
- Avec les 17 articles hors tarif issus de la matrice, on obtient **346 articles**.
- La matrice compte 160 lignes, 558 coches, 16 renvois et 8 cellules « From S/N ».
