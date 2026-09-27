# 03 — Plan par phases

## Décisions à valider

Chaque ligne donne ma recommandation ; si vous validez sans commentaire, elle s'applique.

| # | Sujet | Recommandation |
|---|---|---|
| D1 | Où développer | **Tout en local** : Claude Code sur votre ordinateur, via l'app Desktop ou `claude remote-control` dans le dossier du projet, pilotable depuis l'application. L'application tourne de toute façon en local (127.0.0.1, hors ligne). Continuer en cloud reste possible, mais le PDF devra être renvoyé à chaque nouvelle session et vous ne verrez l'application qu'en captures d'écran. |
| D2 | Ce qui entre dans git | **Uniquement le code, la configuration et la documentation, sans aucun prix.** Restent hors git dans `data/` : PDF, base, vignettes, rapports, valeurs golden, catalogue JSON. Un test d'hygiène échoue si un de ces fichiers est suivi. Dépôt privé conseillé si vous gardez GitHub ; public acceptable avec cette règle. |
| D3 | Arbitrages manuels | Fichier versionné `config/overrides/evolis-cismea.yml`, sans prix. Il contient les alias de codes (ex. R4F226NAAA → R2F226NAAA), les confirmations de composants de bundle et les anomalies acceptées. **Rien n'est appliqué sans une ligne écrite par vous**, et chaque ligne est citée dans le rapport d'import. |
| D4 | Flag agrégé d'un article | N > D > I > aucun ; toute divergence donne une anomalie non bloquante. |
| D5 | Catégorie | Une catégorie principale plus un indicateur `is_bundle`. B22U0000RS : imprimante et bundle. GO PACK, QTM306GRH-BS000-MB1 et les bundles de tablettes -MB1 : catégorie bundle. |
| D6 | Familles ↔ modèles de la matrice | `config/evolis-models.yml` : l'import propose la correspondance (BADGY → Badgy100 & 200…), vous la validez une fois. Elle sert à « consommable incompatible avec l'imprimante du devis » et aux équivalences. |
| D7 | Arrondis des devis | Centimes, arrondi commercial par ligne, TVA sur le total HT par taux (02, « Règles de calcul »). |
| D8 | Hypothèses de TCO | `config/tco.yml` : impressions par face selon le ruban, fréquence de nettoyage… Ces hypothèses sont affichées dans l'UI, car ce ne sont pas des données du PDF. |
| D9 | Équivalences préconfiguré ⇔ base + kits | Calculées et marquées « calculé », jamais présentées comme une donnée Evolis. |
| D10 | Sauvegarde | `tarifs backup` : copie à chaud de la base (API backup de SQLite) avec rotation, vers un dossier de votre choix, par exemple synchronisé avec Drive. |
| D11 | Identité visuelle Celer-IT | Logo Celer-IT dans l'en-tête de l'application (phase 3) et des devis (phase 5). Badge « Evolis Platinum Reseller 2026/2027 » en pied des devis clients, désactivable. Fichiers dans `assets/branding/`. Les coordonnées de la société sont saisies dans les paramètres, jamais inventées. |

## Stack : aucune objection bloquante

La stack imposée est confirmée : Python 3.12 + uv, pdfplumber, PyMuPDF, pydantic, SQLite, FastAPI sur 127.0.0.1, Vite + React + TypeScript + Tailwind, MiniSearch. Elle s'installe sans problème (vérifié).

Ajouts mineurs :

- **Côté Python** : `typer` (CLI), `uvicorn`, `openpyxl` (XLSX en import et en export), `PyYAML`, `ruff`.
- **Côté front** : `@tanstack/react-virtual`, `vitest`.
- **PDF des devis** : via PyMuPDF, déjà présent, plutôt que WeasyPrint et ses dépendances natives.
- **Node** : nécessaire seulement pour construire le front. `tarifs serve` sert ensuite `web/dist` hors ligne.

Suggestion : le PDF est un export Excel. Si Evolis peut vous fournir le **fichier XLSX source**, l'import tabulaire de la phase 6 deviendrait la voie la plus sûre pour les mises à jour. Le parser PDF resterait la référence tant que ce n'est pas le cas.

## Arborescence visée

```
pyproject.toml                 uv ; script `tarifs` = tarifs.cli:app
src/tarifs/
  cli.py                       import · check · inspect · serve · backup
  pdf/                         styles (police/taille/couleur), grille, cellules, lignes logiques, rendus/crops
  importers/base.py            PriceListParser → ParsedPriceList (pydantic)
  importers/evolis.py          gabarit Evolis (tarif + matrice), sélection par empreinte
  importers/generic.py         phase 6 : find_tables() + mapping de colonnes
  importers/tabular.py         phase 6 : CSV/XLSX + mapping
  enrich/                      catégories et attributs (§3.4), notes → relations et conditions, bundles
  checks/                      anomalies, réconciliation par page, import_report.md
  db/                          schema.sql, migrations, accès
  api/                         FastAPI (127.0.0.1)
  quotes/                      calculs, contrôles, exports (phase 5)
  tco/                         phase 6
config/                        synonyms.yml, overrides/, evolis-models.yml, tco.yml
assets/branding/               logo Celer-IT, badge Evolis Platinum Reseller
web/                           Vite + React + TypeScript + Tailwind
tests/                         pytest (unitaires synthétiques ; golden si le PDF est présent)
tools/analysis/                sondes de la phase 1
data/                          HORS GIT : sources/, tarifs.db, crops/, reports/, golden/
docs/                          01 analyse · 02 schéma · 03 plan
```

## Phases

Chaque phase se termine par : tests verts, courte démonstration, commit, et un résumé de 5 lignes maximum (ce qui marche, ce qui reste, anomalies ouvertes).

### Phase 2 — Import Evolis → SQLite (cœur)

1. **Squelette.** Projet uv, CLI `tarifs import <fichier> [--parser] [--force] [--activate]`, `tarifs check`, `tarifs inspect <pdf> --pages …` (rendus et dumps, pour analyser les prochaines versions) et `tarifs backup`.
2. **Lecture du tarif.**
   - Classification des pages et des styles (01, §3).
   - Tableaux détectés par leurs libellés ; grille lue sur les `rects` ; caractères affectés aux cellules par leur centre.
   - Lignes logiques (wrap ou saut), en conservant les lignes brutes.
   - Codes coupés ou avec astérisque ; prix (U+0020, U+00A0, U+202F, « (1) ») ; conditionnement ; flags de marge.
   - Famille et section propagées, y compris d'une page à l'autre ; notes en italique liées aux lignes.
3. **Notes → relations et conditions** (01, §4.10), détectées sur le texte joint.
4. **Matrice.**
   - Colonnes et groupes (partition par programmation dynamique) ; sections ; lignes, la dernière étant fermée par l'en-tête suivant.
   - Coches, avec le seuil de 25 % du pas ; renvois et notes ; cellules S/N.
   - Motifs `xxx` développés ; articles hors tarif créés.
5. **Enrichissement** (§3.4) et **bundles**, résolus par niveaux et par les overrides.
6. **Stockage** idempotent par SHA-256. `--force` reconstruit la version en conservant les identifiants.
7. **Contrôles.** Anomalies, réconciliation par page (lignes produites = jetons-codes de la bande Product Code, tolérance 0), `data/reports/<version>/import_report.md`, contrôle du sommaire p.2 contre les titres détectés.
8. **Vignettes.** Rendu PNG de chaque ligne, à l'échelle 2 (PyMuPDF).
9. **Tests.**
   - Golden : les valeurs du §3.5 dans `data/golden/…yml`, hors git ; tests sautés si le PDF est absent.
   - Unitaires sur entrées synthétiques : normalisation, prix, jonction des codes, wrap ou saut, partition des groupes, motifs `xxx`, agrégat des flags, détection des notes, hygiène du dépôt.

**Sortie :**

- tests verts ;
- 0 anomalie bloquante ;
- réconciliation OK sur les 27 pages ;
- comptages affichés (attendus : 593 contextes, 329 + 17 articles) ;
- contrôle visuel des vignettes sur un échantillon de pages.

L'équivalence PM2-0001-M + S10281 + S10112 = PM2-0005 est testée en phase 4, avec son moteur ; en phase 2, on vérifie seulement les prix des articles concernés.

### Phase 3 — Recherche (UI)

- **API** (FastAPI, 127.0.0.1) : versions, catalogue JSON, fiche article, anomalies, synonymes, fichiers (PDF, vignettes).
- **Omnibox et parseur de requête.**
  - Normalisation, puis détection d'intention : code, texte, montant seul, liste de références.
  - Opérateurs de prix (`<500`, `>1000`, `1000-2000`, `~1500`, `=250`, `250€`) et filtres préfixés (`gamme:`, `cat:`, `compat:`, `flag:`).
  - Recherche inverse par montant ; multi-références (collage de mail) avec « tout ajouter au devis ».
- **Moteur de codes** : exact > préfixe > contient ; une seule substitution ou transposition tolérée, uniquement si aucun résultat.
- **MiniSearch** : ET entre mots ; préfixe sur le dernier mot ; flou à distance 1 pour les mots de 5 lettres ou plus ; boost name > details > gamme ; pas de sous-chaîne pour les jetons de moins de 3 caractères ; synonymes FR → EN.
- **Interface.**
  - En-tête avec le logo Celer-IT et le nom de l'application ; en thème sombre, le logo est posé sur une pastille claire.
  - Facettes à compteurs dynamiques et histogramme des prix.
  - Table virtualisée ; fiche latérale (contextes, vignette, bouton PDF `#page=N`, notes et conditions).
  - Raccourcis du §5.6 ; thème clair/sombre ; formats fr-FR.
- **Tests Vitest** : les 20 requêtes de référence ; temps par frappe mesuré inférieur à 50 ms sur le catalogue réel.
- **Lancement** : `uv run tarifs serve` sert le front construit et ouvre le navigateur.

**Sortie** : requêtes de référence OK et moins de 50 ms par frappe.

### Phase 4 — Compatibilités, relations, bundles

- Fiche imprimante : consommables compatibles groupés par type et triés par €/impression, modèles discontinués inclus. Filtre `compat:`.
- Relations requires et recommends affichées dans les deux sens, avec leurs conditions (MOQ, ERC, disponibilité, S/N).
- Bundles : composants, niveau de résolution, économie par rapport à l'achat séparé (seulement si tous les composants sont résolus).
- Équivalences calculées « préconfiguré ⇔ base + kits + pièces obligatoires » à partir des attributs (modèle, faces, couleur, connectivité, encodeur) et des relations requires.
- Écran Anomalies ; lecture des overrides.

**Tests** : compatibilités golden (R5F002EAA, R5F202M100, RT4F010EAA, ACL004) et équivalences (PM2-0005, ZN1HB000RS).

### Phase 5 — Pré-devis

- Panier alimenté de partout : touche Entrée, bouton, multi-références. Sections, lignes libres, port, remise par ligne et remise globale.
- Paramètres : remise fournisseur, coefficient ou taux de marque cible, TVA.
- Calculs selon 02 ; prix figés avec la version du tarif.
- Contrôles :
  - pièce obligatoire manquante (encodeur sans S10112 ou S10465, module CLM autonome sans A5017) ;
  - MOQ non atteint ;
  - quantité non multiple du conditionnement, avec suggestion ;
  - consommable incompatible avec l'imprimante du devis ;
  - article « contact us for availability » ou sur demande.
- Sauvegarde, duplication et recherche des devis.
- Exports TSV, CSV, XLSX, PDF et Markdown, en mode client ou interne. Les montants sont bruts dans le TSV et le CSV : le format fr-FR utilise U+202F, que Excel n'interprète pas comme un nombre au collage.
- Identité visuelle des devis PDF et XLSX :
  - en-tête avec le logo Celer-IT et les coordonnées de la société, saisies dans les paramètres ;
  - badge « Evolis Platinum Reseller 2026/2027 » en pied de page, désactivable ;
  - rappel de renouvellement du badge une fois passée sa date de fin, elle aussi saisie dans les paramètres.

**Tests** : totaux, arrondis, TVA, remises, marges, contrôles.

### Phase 6 — Versions, configurateur, TCO, imports génériques, veille prix

- **Versions** : diff entre versions (nouveaux, supprimés, variations en € et en %, tri par impact, export) ; alerte sur les devis ouverts dont un prix a changé. Cohérence des flags : un « I » dont le prix a baissé déclenche une anomalie.
- **Configurateur** : modèle → faces → connectivité → encodage → options. Il propose la référence préconfigurée si elle existe, sinon base + kits + pièces obligatoires, avec comparaison de prix. Les règles viennent des sections OPTIONS et des relations, sans codage en dur.
- **TCO** (`config/tco.yml`) : comparaison de 2 à 3 imprimantes et ajout au devis en un clic.
- **Imports génériques** : PDF inconnu (`find_tables()` et écran de mapping) et CSV/XLSX avec le même écran.
- **Veille prix** : prix constaté, source et date, avec l'écart affiché dans la fiche et dans le panier.

**Sortie** : démonstration.
