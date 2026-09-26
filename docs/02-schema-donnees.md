# 02 — Schéma de données (SQLite, `data/tarifs.db`)

Ce schéma part de la proposition du §6 du cahier des charges et l'ajuste d'après l'analyse (voir 01).

Principes :

- **Montants** : toujours en entiers, en centimes.
- **Dates** : texte ISO 8601.
- **Coordonnées** : points PDF, origine en haut à gauche, comme pdfplumber.
- **Traçabilité** : chaque valeur extraite remonte à un contexte (page et bbox).
- **Valeurs dérivées** (coût par impression, équivalences…) : calculées à la lecture, jamais stockées comme si elles venaient d'Evolis.

## Écarts par rapport au §6

| Changement | Pourquoi |
|---|---|
| `article_context` porte son propre prix, son flag, son conditionnement et ses lignes brutes | Détecter les divergences entre contextes : 3 flags et 6 descriptions différentes sur ce PDF |
| Nouvelle table `condition` (MOQ, disponibilité, installation ERC, restriction, S/N minimal), rattachée à un article ou à un seul contexte | « Not recommended for PVC Cards » ne vaut que dans le contexte AGILIA, « Supported on Zenius 2 Expert only » que dans ZENIUS 2 |
| `relation.resolution` et `candidates` | Résolution des composants de bundle par niveaux, sans deviner (01, §4.11) |
| Nouvelle table `printer_model` (colonne, groupe, statut discontinué, modules requis) | Les 19 colonnes de la matrice, avec « + CLM (S10212, S10252) » |
| `compat.checked` à 0 possible | Cellules « From S/N » sans coche |
| Nouvelles tables `anomaly`, `family_model`, `setting`, `favorite`, `recent`, `saved_search` | Écran Anomalies, compatibilité imprimante/devis, paramètres, confort |
| `article.is_bundle` en plus de `category` | Exemple : B22U0000RS est une imprimante vendue en bundle |

## DDL proposé

```sql
-- ─── Versions de tarif ────────────────────────────────────────────────
CREATE TABLE supplier (
  id    INTEGER PRIMARY KEY,
  name  TEXT NOT NULL UNIQUE                    -- 'Evolis'
);

CREATE TABLE price_list (
  id              INTEGER PRIMARY KEY,
  supplier_id     INTEGER NOT NULL REFERENCES supplier(id),
  name            TEXT NOT NULL,                -- 'Price_list-CISMEA-EURO AUG2026 A0'
  zone            TEXT,                         -- 'CISMEA'
  currency        TEXT NOT NULL,                -- 'EUR'
  effective_date  TEXT,                         -- '2026-08-18'
  matrix_ref      TEXT,                         -- 'KB-EHT1-1037-ENG-A3-D2'
  source_file     TEXT NOT NULL,                -- relatif à data/sources/
  sha256          TEXT NOT NULL UNIQUE,         -- import idempotent
  page_count      INTEGER,
  parser          TEXT NOT NULL,                -- 'evolis' | 'generic' | 'tabular'
  parser_version  TEXT NOT NULL,
  imported_at     TEXT NOT NULL,
  status          TEXT NOT NULL CHECK (status IN ('imported','blocked','validated')),
  is_active       INTEGER NOT NULL DEFAULT 0,
  stats           TEXT                          -- JSON : comptages de l'import
);
CREATE UNIQUE INDEX price_list_one_active ON price_list(supplier_id) WHERE is_active = 1;

-- ─── Articles et contextes ────────────────────────────────────────────
CREATE TABLE article (
  id             INTEGER PRIMARY KEY,
  price_list_id  INTEGER NOT NULL REFERENCES price_list(id) ON DELETE CASCADE,
  code           TEXT NOT NULL,                 -- tel qu'imprimé, tirets conservés
  code_norm      TEXT NOT NULL,                 -- majuscules, sans séparateurs
  name           TEXT,                          -- 1re ligne logique de la désignation
  details        TEXT,                          -- lignes logiques suivantes, séparées par \n
  category       TEXT,                          -- printer | ribbon | retransfer_film | laminate | card |
                                                -- cleaning | encoder_kit | hw_option | warranty | software |
                                                -- software_upgrade | accessory | bundle | signature_pad
  is_bundle      INTEGER NOT NULL DEFAULT 0,
  price_cents    INTEGER,                       -- NULL si sur demande ou hors tarif
  on_request     INTEGER NOT NULL DEFAULT 0,
  flag           TEXT CHECK (flag IN ('N','I','D')),  -- agrégat : N > D > I > aucun
  packaging_qty  INTEGER,
  in_price_list  INTEGER NOT NULL DEFAULT 1,    -- 0 = connu uniquement par la matrice
  attrs          TEXT NOT NULL DEFAULT '{}',    -- JSON des attributs typés (§3.4 du cahier des charges)
  UNIQUE (price_list_id, code_norm)
);

CREATE TABLE article_context (
  id             INTEGER PRIMARY KEY,
  article_id     INTEGER NOT NULL REFERENCES article(id) ON DELETE CASCADE,
  page           INTEGER NOT NULL,
  table_no       INTEGER NOT NULL,
  row_no         INTEGER NOT NULL,
  family         TEXT,                          -- propagée depuis la dernière page titrée
  section        TEXT,                          -- propagée, y compris d'une page à l'autre
  x0 REAL, y0 REAL, x1 REAL, y1 REAL,           -- bbox de la ligne
  code_raw       TEXT NOT NULL,                 -- 'CBGR0500F*', 'QTM306GRH-\nBS000-MB1'
  lines          TEXT NOT NULL,                 -- JSON : lignes brutes de la description, avec bbox
  price_raw      TEXT,                          -- texte exact de la cellule, ex. 'd ddd' ou '(1)'
  price_cents    INTEGER,
  on_request     INTEGER NOT NULL DEFAULT 0,
  packaging_qty  INTEGER,
  flag           TEXT CHECK (flag IN ('N','I','D')),
  crop_path      TEXT                           -- data/crops/<version>/p<page>_t<table>_r<row>.png
);
CREATE INDEX article_context_article ON article_context(article_id);

CREATE TABLE footnote (                          -- « * … », « (1) … », notes de la matrice
  id             INTEGER PRIMARY KEY,
  price_list_id  INTEGER NOT NULL REFERENCES price_list(id) ON DELETE CASCADE,
  page           INTEGER NOT NULL,
  scope          TEXT NOT NULL CHECK (scope IN ('table','matrix')),
  marker         TEXT NOT NULL,
  text           TEXT NOT NULL,
  x0 REAL, y0 REAL, x1 REAL, y1 REAL
);
CREATE TABLE context_footnote (
  context_id   INTEGER NOT NULL REFERENCES article_context(id) ON DELETE CASCADE,
  footnote_id  INTEGER NOT NULL REFERENCES footnote(id) ON DELETE CASCADE,
  PRIMARY KEY (context_id, footnote_id)
);

CREATE TABLE condition (                         -- conditions commerciales et techniques, traçables
  id          INTEGER PRIMARY KEY,
  article_id  INTEGER NOT NULL REFERENCES article(id) ON DELETE CASCADE,
  context_id  INTEGER REFERENCES article_context(id) ON DELETE CASCADE,  -- NULL = tous contextes
  kind        TEXT NOT NULL CHECK (kind IN ('moq','availability_on_request','install_by_partner',
                                            'restriction','supported_only','min_serial','on_request_note')),
  value       TEXT,                              -- '4', 'ERC', 'Zenius 2 Expert', '10001082236'
  text_raw    TEXT NOT NULL
);

CREATE TABLE relation (
  id                   INTEGER PRIMARY KEY,
  from_article_id      INTEGER NOT NULL REFERENCES article(id) ON DELETE CASCADE,
  type                 TEXT NOT NULL CHECK (type IN ('requires','recommends','bundle_component')),
  to_code              TEXT,                     -- code cité ou déduit
  to_text              TEXT,                     -- composant en texte libre
  qty                  INTEGER,
  condition            TEXT,                     -- ex. 'stand_alone' (câble A5017)
  note                 TEXT,                     -- phrase source
  resolved_article_id  INTEGER REFERENCES article(id),
  resolution           TEXT NOT NULL CHECK (resolution IN ('cited','suffix','name_exact','name_tokens',
                                                           'override','ambiguous','unresolved')),
  candidates           TEXT,                     -- JSON : codes candidats si ambigu
  source_context_id    INTEGER REFERENCES article_context(id)
);

-- ─── Compatibilité ────────────────────────────────────────────────────
CREATE TABLE printer_model (
  id             INTEGER PRIMARY KEY,
  price_list_id  INTEGER NOT NULL REFERENCES price_list(id) ON DELETE CASCADE,
  col_no         INTEGER NOT NULL,              -- 0..18
  label          TEXT NOT NULL,                 -- 'Primacy2 + CLM (S10212, S10252)'
  name           TEXT NOT NULL,                 -- 'Primacy2 + CLM'
  base_name      TEXT,                          -- 'Primacy2'
  group_name     TEXT NOT NULL,                 -- 'ID RANGE' | … | 'DISCONTINUED'
  discontinued   INTEGER NOT NULL,
  module_codes   TEXT,                          -- JSON ['S10212','S10252']
  UNIQUE (price_list_id, name)
);

CREATE TABLE compat (                            -- ce que dit la matrice, brut
  id                INTEGER PRIMARY KEY,
  price_list_id     INTEGER NOT NULL REFERENCES price_list(id) ON DELETE CASCADE,
  page              INTEGER NOT NULL,
  section           TEXT NOT NULL,
  code_pattern      TEXT NOT NULL,              -- 'R5F002xxx' ou code exact
  description       TEXT,
  prints_raw        TEXT,
  printer_model_id  INTEGER NOT NULL REFERENCES printer_model(id),
  checked           INTEGER NOT NULL,           -- 0 = cellule « From S/N » sans coche
  note_marker       TEXT, note_text TEXT,
  min_serial        TEXT,
  x0 REAL, y0 REAL, x1 REAL, y1 REAL           -- bbox de la cellule
);

CREATE TABLE article_printer (                   -- compatibilité résolue (motifs xxx développés)
  article_id        INTEGER NOT NULL REFERENCES article(id) ON DELETE CASCADE,
  printer_model_id  INTEGER NOT NULL REFERENCES printer_model(id) ON DELETE CASCADE,
  compat_id         INTEGER NOT NULL REFERENCES compat(id) ON DELETE CASCADE,
  note              TEXT,
  min_serial        TEXT,
  PRIMARY KEY (article_id, printer_model_id)
);

CREATE TABLE family_model (                      -- famille du tarif ↔ modèles de la matrice (config validée)
  price_list_id     INTEGER NOT NULL REFERENCES price_list(id) ON DELETE CASCADE,
  family            TEXT NOT NULL,
  printer_model_id  INTEGER NOT NULL REFERENCES printer_model(id) ON DELETE CASCADE,
  PRIMARY KEY (price_list_id, family, printer_model_id)
);

-- ─── Contrôle d'import ────────────────────────────────────────────────
CREATE TABLE anomaly (
  id             INTEGER PRIMARY KEY,
  price_list_id  INTEGER NOT NULL REFERENCES price_list(id) ON DELETE CASCADE,
  severity       TEXT NOT NULL CHECK (severity IN ('blocking','warning','info')),
  kind           TEXT NOT NULL,                 -- ex. 'flag_divergence', 'matrix_near_code'
  code           TEXT,
  page           INTEGER,
  x0 REAL, y0 REAL, x1 REAL, y1 REAL,
  message        TEXT NOT NULL,
  details        TEXT,                          -- JSON
  status         TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','accepted','resolved')),
  resolution     TEXT
);

-- ─── Devis ────────────────────────────────────────────────────────────
CREATE TABLE quote (
  id             INTEGER PRIMARY KEY,
  number         TEXT UNIQUE,                   -- 'D-2026-0001'
  client         TEXT,
  title          TEXT,
  created_at     TEXT NOT NULL,
  updated_at     TEXT NOT NULL,
  price_list_id  INTEGER NOT NULL REFERENCES price_list(id),   -- version utilisée
  status         TEXT NOT NULL DEFAULT 'draft',
  params         TEXT NOT NULL DEFAULT '{}',    -- JSON : remise fournisseur, coefficient ou taux de marque,
                                                -- TVA, remise globale (% ou €), port, imprimante(s) du devis, en-tête
  notes          TEXT
);

CREATE TABLE quote_line (
  id                    INTEGER PRIMARY KEY,
  quote_id              INTEGER NOT NULL REFERENCES quote(id) ON DELETE CASCADE,
  position              INTEGER NOT NULL,
  kind                  TEXT NOT NULL CHECK (kind IN ('article','free','section','shipping')),
  section               TEXT,
  article_id            INTEGER REFERENCES article(id) ON DELETE SET NULL,
  code                  TEXT,                   -- figé : le devis survit à la suppression d'une version
  label                 TEXT NOT NULL,          -- figé
  qty                   INTEGER NOT NULL DEFAULT 1,
  unit_price_cents      INTEGER,                -- prix catalogue figé
  discount_pct          REAL NOT NULL DEFAULT 0,
  purchase_price_cents  INTEGER,                -- prix d'achat figé
  note                  TEXT
);

-- ─── Confort, paramètres, veille (clés par code : survivent aux versions) ───
CREATE TABLE setting      (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE favorite     (supplier_id INTEGER NOT NULL, code_norm TEXT NOT NULL, added_at TEXT NOT NULL,
                           PRIMARY KEY (supplier_id, code_norm));
CREATE TABLE recent       (supplier_id INTEGER NOT NULL, code_norm TEXT NOT NULL, viewed_at TEXT NOT NULL);
CREATE TABLE saved_search (id INTEGER PRIMARY KEY, name TEXT NOT NULL, query TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE street_price (id INTEGER PRIMARY KEY, supplier_id INTEGER NOT NULL, code_norm TEXT NOT NULL,
                           price_cents INTEGER NOT NULL, source TEXT NOT NULL, url TEXT,
                           observed_at TEXT NOT NULL, note TEXT);   -- phase 6
CREATE TABLE schema_version (version INTEGER NOT NULL);
```

## Règles de calcul (devis)

- Prix d'achat = arrondi(catalogue × (1 − remise fournisseur)).
- Net de ligne = arrondi(quantité × prix unitaire × (1 − remise de ligne)). L'arrondi est commercial (ROUND_HALF_UP) au centime, **ligne par ligne**.
- Total HT = somme des lignes, moins la remise globale (en % ou en €), plus le port.
- TVA = arrondi(total HT × taux) : **une fois sur le total HT**, pour chaque taux. TTC = HT + TVA.
- Marge = net − achat. Taux de marque = marge ÷ net. Coefficient = net ÷ achat. La cible (coefficient ou taux de marque) sert d'indicateur ligne par ligne.

## Recherche

Le front reçoit un catalogue JSON compact par version (`/api/catalog?version=`), dont les champs sont calculés côté serveur :

- **articles** : code, code_norm, name, details, category, prix, flag, packaging, attrs ;
- **pour chaque article** : contextes résumés, identifiants des modèles compatibles, relations et coûts unitaires (€/impression, €/carte).

L'index MiniSearch et le moteur de codes tournent en mémoire dans le navigateur, sur environ 350 articles aujourd'hui et moins de 5 000 demain. Les synonymes FR → EN viennent de `config/synonyms.yml`.
