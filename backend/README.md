# Backend CTO Transaction Analyzer

API REST FastAPI pour analyser les exports CSV d'opérations d'un compte-titres BoursoBank.

L'API prend en charge :

- le chargement d'un ou plusieurs exports CSV ;
- le dédoublonnage et le tri des operations ;
- la catégorisation des operations ;
- l'appariement FIFO des achats et des ventes ;
- le calcul des performances par titre ;
- le suivi des virements, retraits et coupons/dividendes ;
- la consultation des positions ouvertes et fermées.

## Prerequis

Depuis la racine du projet :

```bash
uv sync
```

Pour lancer les tests depuis la racine :

```bash
uv run pytest -q
```

## Configuration

La configuration est gerée par `app/core/config.py` avec `pydantic-settings`.
Un modèle de configuration est disponible dans `.env.example` au niveau du backend.
Les valeurs peuvent être définies dans un fichier dans `backend/.env` faire `cp .env.example .env`.

Les variables d'environnement du système restent prioritaires.

| Variable | Defaut | Description |
| --- | --- | --- |
| `PROJECT_NAME` | `BoursoBank CTO Analyzer API` | Nom de l'API dans OpenAPI |
| `API_VERSION` | `0.0.1` | Version exposee par l'API |
| `BACKEND_HOST` | `127.0.0.1` | Adresse d'ecoute recommandée |
| `BACKEND_PORT` | `8000` | Port de l'API |
| `FRONTEND_HOST` | `http://localhost:8501` | Origine autorisée par CORS |
| `CSV_REQUIRED_COLUMNS` | Colonnes Boursorama standard | Liste separée par des virgules des colonnes à vérifier et utiliser pour le dédoublonnage |



## Lancement

Depuis la racine du projet :

```bash
uv run uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

L'API est alors disponible à l'adresse `http://localhost:8000`.

- Documentation interactive Swagger : `http://localhost:8000/docs`
- Documentation ReDoc : `http://localhost:8000/redoc`
- Vérification de sante : `http://localhost:8000/api/health`

Pour utiliser une autre adresse ou un autre port, adaptez les options Uvicorn et la variable `BACKEND_URL` du frontend.

## Format d'import (pour l'instant spécifique à BoursoBank)

L'endpoint d'import attend un ou plusieurs fichiers CSV BoursoBank, avec :

- séparateur `;` ;
- encodage UTF-8 avec BOM accepte ;
- une ligne d'en-tête contenant les colonnes suivantes :

```text
Date opération;Date valeur;Opération;Valeur;Code ISIN;Montant;Quantité;Cours
```

Les dates doivent respecter le format `JJ/MM/AAAA`. Les cours peuvent contenir un symbole euro, des espaces et une virgule décimale, par exemple `1 234,50 €`.

Les opérations sont classées selon leur libelle :

| Libelle contenant | Categorie |
| --- | --- |
| `ACHAT` | Achat de titres |
| `VENTE` | Vente de titres |
| `COUPON` ou `DIVIDENDE` | Coupon ou dividende |
| `VIR` | Virement |
| autre libelle | Autre |

Les lignes strictement identiques sont retirees lorsque plusieurs fichiers se recouvrent.

La variable `CSV_REQUIRED_COLUMNS` permet d'ajouter des colonnes specifiques a un export ou de modifier la liste controlee. Les huit colonnes metier standard restent necessaires au traitement actuel, car elles sont utilisees pour les dates, la categorisation, le FIFO et les calculs financiers.

## Endpoints

### Creer une session d'analyse

```http
POST /api/sessions
Content-Type: multipart/form-data
```

Le champ multipart `files` accepte plusieurs fichiers CSV.
La reponse contient un `session_id`, un resume de l'import et les avertissements FIFO eventuels.

### Consulter une session

| Methode | Route | Contenu |
| --- | --- | --- |
| `GET` | `/api/sessions/{session_id}/titres` | Liste des titres |
| `GET` | `/api/sessions/{session_id}/transactions` | Achats et ventes |
| `GET` | `/api/sessions/{session_id}/positions/fermees` | Positions appariees en FIFO |
| `GET` | `/api/sessions/{session_id}/positions/ouvertes` | Lots encore ouverts |
| `GET` | `/api/sessions/{session_id}/stats-titres` | Statistiques par titre |
| `GET` | `/api/sessions/{session_id}/tresorerie` | Virements et coupons |
| `GET` | `/api/sessions/{session_id}/lignes-non-categorisees` | Operations a verifier |
| `GET` | `/api/sessions/{session_id}/graphique/{titre}` | Donnees du graphique d'un titre |

Une session inconnue renvoie `404`.

## Tests

Les tests unitaires couvrent les services de parsing, categorisation, dedoublonnage, FIFO, tresorerie et statistiques.

Depuis la racine du projet :

```bash
uv run pytest -q
```

## Organisation du code

```text
backend/
├── app/
│   ├── core/config.py           # configuration et variables d'environnement
│   ├── main.py                  # application FastAPI et routes HTTP
│   ├── models/session.py        # structure interne d'une session
│   └── services/transactions.py # logique d'analyse des exports
├── tests/test_transactions.py   # tests unitaires
└── README.md
```


## Limites connues

- Les sessions sont stockees uniquement en memoire et sont perdues au redemarrage du processus.
- Une vente ne peut etre appariee que si l'achat correspondant est present dans les fichiers importes.
- L'API est prevue pour un usage local mono-utilisateur ; un stockage persistant et une authentification seront necessaires pour un usage partage.
