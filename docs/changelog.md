## v0.0.0

#### 03-10-2026

- Ajout d'un bouton Streamlit pour collecter les exports `export-operations-*.csv` du dossier Téléchargements du backend.
- Les fichiers collectés sont déplacés vers le dossier configuré par `TRANSACTIONS_DATA_DIR` (par défaut `FINANCE/data/data_transaction`).

#### 01-10-2026

- Gestion des variables avec fichier .env
- Gestion des librairies avec uv
- Modularisation du code front streamlit

### Premières versions avec premières idées

Objectif :

- Débuter avec un notebook pour explorer et s'assurer que tout fonctionne comme attendu
- Puis développer une première API avec un frontend streamlit simple
- Et enfin améliorer le frontend

Idées à date :

#### 21-08-2026

- Visualiser les transactions (à quel moment j'ai acheté ? à quel moment j'ai vendu ?)
- Ce que j'ai gagné/perdu par action
- Par rapport au cours actuel, est-il intéressant de (re)rentrer ? Avec indicateurs techniques sur l'action (RSI, MMn ect)

#### 23-08-2026

- Pousser dans git une première version de visualisation
- Automatiser la récupération des fichiers téléchargés (opérations, positions) [extraction manuelle, car pas possible de requêter directement BoursoBank]
