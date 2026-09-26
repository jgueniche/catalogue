# Sondes d'analyse (phase 1)

Scripts jetables qui ont servi à écrire `docs/01-analyse-pdf-evolis-cismea.md`.
Ce ne sont **pas** le parser : celui-ci est écrit proprement en phase 2 (`src/tarifs/`).
Toutes les sorties vont dans `data/analysis/` (hors git).

| Script | Rôle |
|---|---|
| `render_pages.py [pdf] [out] [dpi]` | rendu PNG de chaque page (150 dpi par défaut) |
| `dump_page.py <out> <page>...` | mots et caractères (coordonnées, police, taille, couleurs) + rects/courbes/images |
| `probe_tables.py [pdf] [out]` | tableaux de prix : en-têtes par libellés, grille, cellules, flags, statistiques |
| `probe_matrix.py [pdf] [out]` | matrice : colonnes, groupes, coches, renvois, S/N, résolution des codes (lit la sortie de `probe_tables.py`) |

Lancer depuis la racine du dépôt avec l'environnement du projet (pdfplumber, PyMuPDF).
