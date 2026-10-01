# Analyse CTO BoursoBank — Back (FastAPI) + Front (Streamlit)

Analyse d'export(s) CSV "Historique des opérations" BoursoBank (CTO) :
appariement FIFO achats/ventes, statistiques de performance par titre,
suivi de trésorerie (virements et coupons/dividendes).

## Structure

```
BoursoBank-analyzer/
├── backend/
│   ├── app/
│   │   ├── core/config.py            # variables d'environnement et réglages
│   │   ├── models/session.py         # modèle des sessions d'analyse
│   │   └── services/transactions.py  # parsing, FIFO, stats, trésorerie
│   └── main.py     # API FastAPI
├── frontend_streamlit/               # streamlit dans un premier temps
│   └── app.py      # interface Streamlit qui consomme l'API
├── tests/
│   └── test_transactions.py # tests unitaires des services
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── uv.lock
└── README.md
```

## Installation

Installer `uv` si nécessaire, puis synchroniser l'environnement depuis la racine :

```bash
uv sync
```

Cette commande crée l'environnement virtuel `.venv` et installe les dépendances
de l'application et de développement. Le fichier `uv.lock` verrouille les
versions résolues.

Copier `.env.example` vers `.env` et adapter les valeurs si nécessaire.

Pour installer les dépendances de développement et lancer les tests :

```bash
uv run pytest tests -q
```

## Lancement

Deux process séparés, dans deux terminaux.

**1. Backend (API)**

```bash
uv run uvicorn app.main:app --app-dir backend --reload --port 8000
```

L'API est alors disponible sur `http://localhost:8000` (doc interactive
auto-générée sur `http://localhost:8000/docs`).

**2. Frontend (Streamlit)**

```bash
uv run streamlit run frontend_streamlit/app.py
```

Par défaut le front cherche le backend sur `http://localhost:8000`. Pour
pointer ailleurs (autre machine, autre port) :

```bash
BACKEND_URL=http://mon-serveur:8000 uv run streamlit run frontend_streamlit/app.py
```

## Utilisation

1. Dans la barre latérale, importe un ou plusieurs fichiers CSV BoursoBank
   (un export par mois par exemple — les périodes qui se chevauchent sont
   automatiquement dédoublonnées).
2. Clique sur **Analyser**.
3. Trois onglets :
   - **Performance par titre** : stats agrégées, positions clôturées et positions
     encore ouvertes.
   - **Détail d'un titre** : graphique interactif (achats/ventes/points d'entrée)
     pour un titre choisi dans la liste déroulante.
   - **Trésorerie** : total des virements entrants/sortants et des coupons perçus,
     ventilés par titre.

## Format CSV attendu

Export BoursoBank, séparateur `;`, encodage UTF-8 (avec BOM), colonnes :
`Date opération`, `Date valeur`, `Opération`, `Valeur`, `Code ISIN`, `Montant`,
`Quantité`, `Cours`.

Catégorisation automatique de la colonne `Opération` :
- contient "ACHAT" → achat de titres
- contient "VENTE" → vente de titres
- contient "COUPON" ou "DIVIDENDE" → coupon/dividende perçu
- contient "VIR" → virement (dépôt si montant positif, retrait si négatif)
- sinon → "autre" (frais, régularisations...), affiché à part car non pris en
  compte dans les totaux calculés — à vérifier manuellement au cas par cas.

## Limites connues / pistes d'évolution

- Le matching FIFO ne peut apparier une vente que si l'achat correspondant
  figure dans les fichiers importés. Si ton historique exporté ne remonte pas
  jusqu'au premier achat d'un titre, un avertissement est affiché plutôt
  qu'un résultat silencieusement faux.
- Les sessions d'analyse sont stockées en mémoire côté API (pas de base de
  données) : elles sont perdues si le process backend redémarre. Suffisant en
  usage local mono-utilisateur ; à changer (Redis, base de données) si le
  projet doit être partagé ou survivre à des redémarrages fréquents.
- Pas encore de comparaison avec le cours de bourse actuel (pour cibler de
  nouveaux points d'entrée à partir d'aujourd'hui) — évolution possible via
  une source de cours en temps réel.
