# MedHistory

Personal medical history management system with AI-powered document analysis and lab result interpretation.

## Overview

MedHistory solves the problem of medical document fragmentation across clinics, labs, and archives. Users upload documents (PDFs, photos of results, prescriptions), and the system automatically classifies them, extracts key data, and builds a structured medical timeline.

**Live:** [medhistory.ru](https://medhistory.ru)

## Features

- **Automatic document classification** — AI categorizes uploaded files (blood tests, MRI, prescriptions, doctor visits, etc.) and extracts dates, medical institution, and specialty
- **Interactive medical timeline** — visual chronology of all medical events with filtering by specialty, document type, and time period
- **AI lab result interpretation** — trend analysis over time with plain-language explanations of deviations from reference ranges
- **Report generation** — structured medical summaries in PDF format for sharing with doctors
- **Family accounts** — separate profiles for each family member with parental access control
- **Telegram bot** — access via Telegram with n8n workflow automation

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript, Vite, Zustand, TanStack Query, Tailwind CSS |
| Backend | FastAPI (Python), SQLAlchemy 2.0 async, Pydantic 2 |
| Databases | PostgreSQL 16, MongoDB 7, MinIO (S3) |
| AI/LLM | OpenRouter → Google Gemini 2.5 Flash |
| Auth | JWT + Google OAuth 2.0 |
| Infrastructure | Docker Compose, Nginx, Let's Encrypt, Cloudflare Tunnel |
| Automation | n8n (Telegram bot workflows) |
| CI/CD | GitHub Actions → Yandex Cloud VM |

## Project Structure

```
medhistory-local/
├── backend/          # FastAPI application
│   ├── app/
│   │   ├── api/      # REST API routes (v1)
│   │   ├── core/     # Config, security, settings
│   │   ├── db/       # DB connections (PostgreSQL, MongoDB, MinIO)
│   │   ├── models/   # SQLAlchemy models
│   │   ├── schemas/  # Pydantic schemas
│   │   └── services/ # Business logic
│   └── migrations/   # Alembic migrations
├── frontend/         # React application
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── services/ # API client
│       └── stores/   # Zustand stores
├── nginx/            # Reverse proxy config (SSL, rate limiting)
├── n8n/              # Telegram bot workflow definitions
├── monitoring/       # Prometheus + Grafana (optional)
├── scripts/          # Data seeding & analyte mapping utilities
├── docker-compose.yml
├── docker-compose.prod.yml
└── deploy.local      # Local deployment script
```

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Copy `.env.local.example` → `.env.local` and fill in the required values (see [Environment Variables](#environment-variables))

### Run Locally

```bash
./deploy.local
```

Or manually:

```bash
docker compose -p medhistory --env-file .env.local up -d
```

### Deployment Options

```bash
./deploy.local                # Standard startup
./deploy.local --rebuild      # Rebuild Docker images
./deploy.local --monitoring   # Include Prometheus & Grafana
./deploy.local --clean-data   # Wipe data and start fresh
./deploy.local --update       # Quick update without rebuilding
```

### Local Service URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| MinIO Console | http://localhost:9001 |
| DB Viewer | http://localhost:5050 |
| n8n (Telegram bot) | http://localhost:5678 |

## Environment Variables

Copy `.env.local` and configure:

```bash
# PostgreSQL
POSTGRES_DB=medhistory
POSTGRES_USER=medhistory_user
POSTGRES_PASSWORD=<password>

# MongoDB
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_PASSWORD=<password>

# MinIO
MINIO_ROOT_USER=minio_admin
MINIO_ROOT_PASSWORD=<password>

# Backend
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/medhistory
MONGODB_URL=mongodb://admin:pass@mongodb:27017/medhistory?authSource=admin
JWT_SECRET=<secret>

# AI
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=google/gemini-2.5-flash

# Google OAuth
GOOGLE_CLIENT_ID=<client-id>
GOOGLE_CLIENT_SECRET=<client-secret>
GOOGLE_REDIRECT_URI=http://localhost:5173/auth/google/callback

# Frontend
VITE_API_URL=http://localhost:8000

# Telegram Bot (n8n)
TELEGRAM_BOT_TOKEN=<token>
N8N_WEBHOOK_URL=https://<tunnel>.trycloudflare.com
```

## Production Deployment

Production runs on a Yandex Cloud VM with GitHub Actions CI/CD.

**Trigger:** Manual dispatch in GitHub Actions (select branch and service to deploy)

**GitHub Secrets required:**
- `SERVER_IP` — VM IP address
- `SERVER_USER` — SSH user
- `SSH_PRIVATE_KEY` — private key for server access

The pipeline rsyncs the codebase to the server, then builds and restarts containers using `docker-compose.prod.yml` and `.env.production`.

HTTPS is handled by Nginx with Let's Encrypt certificates (auto-renewal via Certbot).

## Database Migrations

```bash
# Apply migrations
cd backend
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"
```

## Monitoring (Optional)

```bash
./deploy.local --monitoring
```

Starts Prometheus + Grafana alongside the main stack. Backend exposes metrics at `/metrics`.
