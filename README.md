# CAD 3D Generator

Application web de génération de modèles 3D imprimables via CAO paramétrique (CadQuery) et langage naturel.

## Fonctionnalités

- **Génération IA** : Décrivez votre pièce en langage naturel, l'IA génère le code CadQuery
- **Éditeur de code** : Monaco Editor pour éditer manuellement le code CadQuery
- **Prévisualisation 3D** : Visualisation Three.js avec rotation, zoom et cotes
- **Paramètres éditables** : Modifiez les dimensions directement dans un panneau latéral
- **Contraintes imprimante** : Profils d'imprimante 3D avec validation du volume de build
- **Export** : STL et 3MF compatibles Bambu Studio

## Stack technique

- **Backend** : Python 3.11+, FastAPI, CadQuery, SQLAlchemy (PostgreSQL)
- **Frontend** : Vue 3, TypeScript, Vite, Tailwind CSS, Three.js, Monaco Editor
- **IA** : OpenAI GPT-4 ou Anthropic Claude
- **Déploiement** : Docker, Railway

## Installation locale

### Prérequis

- Python 3.11+
- Node.js 20+
- PostgreSQL 16+
- Docker & Docker Compose (optionnel)

### Avec Docker Compose

```bash
# Copier les variables d'environnement
cp .env.example .env
# Éditer .env avec vos clés API

# Lancer les services
docker compose up -d

# L'application est accessible sur http://localhost:5174
# Backend API sur http://localhost:8042
# PostgreSQL sur le port 5433
```

### Sans Docker

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate sur Windows
pip install -r requirements.txt

# Configurer la base de données
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/cad3d"
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Lancer le backend
uvicorn app.main:app --reload

# Frontend (dans un autre terminal)
cd frontend
npm install
npm run dev
```

## Déploiement Railway

1. Créer un projet Railway et ajouter un service PostgreSQL
2. Connecter le repository GitHub
3. Configurer les variables d'environnement :
   - `DATABASE_URL` (auto-configuré par Railway)
   - `OPENAI_API_KEY`
   - `ANTHROPIC_API_KEY`
   - `DEFAULT_LLM_PROVIDER` (openai ou anthropic)
4. Déployer

```bash
# Ou via CLI
railway login
railway init
railway up
```

## Structure du projet

```
Ai3Dmodel/
├── backend/
│   ├── app/
│   │   ├── main.py              # Point d'entrée FastAPI
│   │   ├── config.py            # Configuration
│   │   ├── database.py          # Connexion PostgreSQL
│   │   ├── models/              # Modèles SQLAlchemy
│   │   ├── schemas/             # Schémas Pydantic
│   │   ├── routers/             # Endpoints API
│   │   ├── services/            # Logique métier
│   │   └── prompts/             # System prompts LLM
│   ├── alembic/                 # Migrations DB
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # Composants Vue
│   │   ├── stores/              # Pinia stores
│   │   ├── services/            # Client API
│   │   └── types/               # Types TypeScript
│   └── package.json
├── Dockerfile
├── docker-compose.yml
└── railway.toml
```

## API Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/projects` | Liste des projets |
| POST | `/api/projects` | Créer un projet |
| GET | `/api/projects/{id}` | Détail projet |
| DELETE | `/api/projects/{id}` | Supprimer projet |
| POST | `/api/projects/{id}/parts` | Ajouter un morceau |
| GET | `/api/parts/{id}` | Détail morceau |
| PUT | `/api/parts/{id}` | Modifier morceau |
| POST | `/api/parts/{id}/generate` | Générer code IA |
| GET | `/api/parts/{id}/preview` | Preview STL |
| GET | `/api/parts/{id}/export/stl` | Export STL |
| GET | `/api/parts/{id}/export/3mf` | Export 3MF |
| GET | `/api/parts/{id}/parameters` | Paramètres extraits |
| PUT | `/api/parts/{id}/parameters` | Modifier paramètres |
| POST | `/api/parts/{id}/validate` | Valider vs volume |
| GET | `/api/printers/presets` | Profils imprimante |

## Imprimantes supportées

- Bambu Lab P1S, X1 Carbon, A1, A1 Mini
- Prusa MK4, Mini+
- Creality Ender 3 V2, Ender 3 S1
- Voron 0.2, 2.4
- Personnalisé

## Licence

MIT
