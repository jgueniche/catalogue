# Catalogue — outil local de recherche dans des tarifs PDF (devis)

Utilisateur unique, usage 100 % local : aucune diffusion, pas de cloud, pas d'authentification, pas de télémétrie.
L'utilisateur travaille chez Celer-IT, revendeur Evolis Platinum. Les devis sortent à l'en-tête Celer-IT.
Échanges et interface en français, formats fr-FR.

## Où est quoi

- Cahier des charges complet : `data/specs/cahier-des-charges.md` (hors git, contient des prix). S'il est absent, le demander à l'utilisateur.
- Phase 1, livrée :
  - `docs/01-analyse-pdf-evolis-cismea.md` : structure du PDF et anomalies attendues ;
  - `docs/02-schema-donnees.md` : schéma SQLite et règles de calcul ;
  - `docs/03-plan-phases.md` : décisions D1–D11 et plan des phases 2 à 6.
- Sondes d'analyse (ce n'est pas le parser) : `tools/analysis/`.
- Tarif source : `data/sources/Price_list-CISMEA-EURO_AUG2026_A0.pdf`
  (SHA-256 `0bd78893a95a2e9a4111736d2a1cc9da1ced25d8375cbe6c6c7e66d3e4546563`).
- Valeurs golden des tests : `data/golden/` (hors git), issues du §3.5 du cahier des charges.
- Identité visuelle : `assets/branding/`, avec le logo Celer-IT et le badge Evolis Platinum Reseller 2026/2027 (décision D11, voir le README du dossier).

## Règles

- Zéro donnée inventée. Toute valeur extraite est traçable (page et bbox). En cas de doute, créer une anomalie, jamais une valeur devinée.
- Rien de `data/` dans git (PDF, base, vignettes, rapports, golden) et aucun prix dans les fichiers versionnés : le dépôt GitHub est public.
- Travail par phases. Une phase se termine par des tests verts, une courte démo et un commit, puis un résumé de 5 lignes maximum (ce qui marche, ce qui reste, anomalies ouvertes). Attendre la validation de l'utilisateur avant la phase suivante.
- Stack imposée :
  - Python 3.12 et uv, pdfplumber, PyMuPDF, pydantic ;
  - SQLite (`data/tarifs.db`), FastAPI lié à 127.0.0.1 uniquement ;
  - Vite, React, TypeScript, Tailwind, MiniSearch.

  Montants en centimes (entiers).

## Statut

- Phase 1 : livrée ; les décisions D1–D11 de `docs/03` attendent la validation de l'utilisateur.
- Phase 2 (import Evolis → SQLite) : à démarrer.
