# 🚂 Railway Traffic Management System

A comprehensive, production-ready Railway Traffic Management System built for real-time train tracking, conflict detection, and traffic optimization. Developed for Smart India Hackathon (SIH).


## 🎯 Features

- **Real-time Train Tracking**: GPS-based position monitoring with WebSocket updates
- **Conflict Detection**: Automated collision risk and traffic conflict identification  
- **Section Management**: Track occupancy monitoring and capacity optimization
- **Controller Dashboard**: Role-based access control for traffic controllers
- **Decision Audit Trail**: Complete logging of all controller decisions
- **Performance Analytics**: Network utilization and efficiency metrics


# 🚆 Low Fidelity UI 
[Image](https://drive.google.com/file/d/1I-xOgjKBz5HkLgsXaEXMkULpQPMaCrIX/view?usp=sharing3)


## 🛠 Tech Stack

**Backend**: FastAPI (Python 3.12+), PostgreSQL 15, TimescaleDB, Redis, SQLAlchemy
**Frontend**: React 18, TypeScript, Vite, D3.js, Tailwind CSS
**Infrastructure**: Docker, Docker Compose, Alembic migrations

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/Auxilus08/DSS_Railway_SIH.git
cd DSS_Railway_SIH
```

### 2. Environment Setup
```bash
cp .env.example .env
cp backend/.env.example backend/.env
# Edit .env files with your configuration
```

### 3. Start with Docker
```bash
docker-compose up --build
```

### 4. Manual Setup (Development)
```bash
# Start database services
docker-compose up postgres redis -d

# Backend setup
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python setup_railway_db.py
uvicorn app.main:app --reload --port 8001

# Frontend setup
cd frontend
npm install
npm run dev
```

## 🌐 Service URLs

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8001  
- **API Docs**: http://localhost:8001/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## 📊 Key Components

### Database Schema
- **trains** - Train information and status
- **sections** - Track sections, junctions, stations  
- **positions** - Real-time positions (TimescaleDB)
- **controllers** - Traffic controller accounts
- **conflicts** - Detected traffic conflicts
- **decisions** - Controller decision audit trail

### API Endpoints
- Authentication: `/api/auth/*`
- Train Management: `/api/trains/*`
- Section Management: `/api/sections/*`
- Real-time: WebSocket `/ws`

## 🧪 Testing

```bash
# Backend tests
cd backend && pytest

# Frontend tests  
cd frontend && npm test

# Performance tests
cd backend/test_scripts && python performance_test.py
```

## 🔒 Security Features

- JWT token authentication
- Role-based access control
- Rate limiting and input validation
- Secure environment configuration

## 📚 Documentation

- **API Docs**: http://localhost:8001/docs
- **Database Guide**: [backend/RAILWAY_README.md](backend/RAILWAY_README.md)
- **API Reference**: [backend/API_DOCUMENTATION.md](backend/API_DOCUMENTATION.md)

## 🏆 Smart India Hackathon 2025

Developed for SIH 2025, addressing railway traffic management modernization with real-time monitoring and intelligent conflict resolution.

---

**Built with ❤️ for Smart India Hackathon 2025**
