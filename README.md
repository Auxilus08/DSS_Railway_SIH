# DSS Railway SIH – Hackathon Stack (FastAPI + React + Postgres + Redis)

Production-ready hackathon starter with Docker Compose. Backend (FastAPI), Postgres 15 with TimescaleDB, Redis (as queue/cache), and React 18 + TypeScript + D3 dev server.

## Tech Stack
- Backend: FastAPI (Python 3.11+)
- DB: PostgreSQL 15 + TimescaleDB extension
- Queue/Cache: Redis (Kafka can be added later)
- Frontend: React 18 + TypeScript + D3.js (Vite)
- Containerization: Docker + Docker Compose

## Quickstart

0. Clone this repository
```
git clone https://github.com/Auxilus08/DSS_Railway_SIH.git
cd DSS_Railway_SIH
```

1. Copy env template and adjust as needed
```
cp .env.example .env
```

2. Start all services
```
docker-compose up --build
# or (if using newer Docker)
docker compose up --build
```

This runs:
- Postgres: 5432
- Redis: 6379
- Backend (FastAPI): http://localhost:8000
- Frontend (Vite dev): http://localhost:5173

## Health checks
- Backend: http://localhost:8000/api/health
- Frontend: http://localhost:5173
- Postgres: container health via pg_isready
- Redis: container health via redis-cli ping

## Database connection test
The backend exposes `/api/db-check` which tests a connection to the configured Postgres instance and returns ok/error JSON.

```
curl -s http://localhost:8000/api/db-check | jq
```

## Project Structure
```
.
├── backend
│   ├── app
│   │   ├── main.py
│   │   └── db.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend
│   ├── index.html
│   ├── src
│   │   ├── main.tsx
│   │   └── App.tsx
│   └── Dockerfile
├── docker
│   └── postgres
│       └── init.sql
├── .env.example
├── docker-compose.yml
├── .gitignore
└── README.md
```

## Notes
- TimescaleDB extension is enabled via init SQL at container startup.
- For Kafka later, add a Kafka service (e.g., Bitnami images) and wire to backend.
- In dev, backend and frontend mount source volumes for hot reload.

## Common commands
- Rebuild a single service
```
docker compose build backend && docker compose up backend
```

- View logs
```
docker compose logs -f backend
```

- Connect to Postgres
```
docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB
```

- Run tests (placeholder):
```
docker compose exec backend pytest
```
