# data/ — hors git

Tout ce dossier est ignoré par git (sauf ce fichier) : il contient des données tarifaires.

| Chemin | Contenu |
|---|---|
| `sources/` | PDF/CSV/XLSX fournisseurs importés |
| `tarifs.db` | base SQLite (versions, articles, relations, compatibilités, devis) |
| `crops/<version>/` | vignettes PNG des lignes (traçabilité dans la fiche article) |
| `reports/<version>/import_report.md` | rapport d'import et anomalies |
| `golden/` | valeurs golden des tests (lues sur le PDF) |
| `analysis/` | sorties des sondes `tools/analysis/` |
| `backups/` | sauvegardes de la base (`tarifs backup`) |
