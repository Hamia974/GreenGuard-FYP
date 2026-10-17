# GreenGuard

AI-powered Plant Health Monitoring and Agricultural Decision Support System.

This is the **frontend** application for GreenGuard, built with Next.js. For AI/module contracts and specifications, see [`/docs`](../docs) in the repository root.

---

## 1. Project Overview

GreenGuard is a production-grade, AI-powered agricultural decision support platform. Farmers upload a leaf image for a registered farm; the backend runs three independent AI modules (disease detection, soil & nutrient health, weather risk) and returns one integrated analysis report showing each module's result side by side.

The system follows a strict layered client–server architecture: the frontend communicates **only** with the Django REST backend, never directly with AI services, the database, or external APIs.

This repository is developed as a Final Year Project (BS Computer Science) and is built to production-quality standards, not as a demo application.

---

## 2. Features

- Plant disease, nutrient deficiency, and insect detection from leaf images
- Soil fertility analysis with N/P/K status and crop + variety recommendations
- Weather risk assessment (fungal disease, heat stress, drought) via the Weather Module (Open-Meteo data)
- Integrated Analysis Report (Module 4) showing the Disease, Soil & Nutrient and Weather results together — no fused "final diagnosis"
- Multi-farm management with per-farm prediction history
- Dashboard with recent predictions, weather summary, and recommendation overview
- Notifications (prediction completed, weather alerts, system announcements)
- JWT authentication with role-based access control (Farmer / Admin)
- Admin dashboard for user, prediction, and AI module monitoring

---

## 3. Tech Stack

**Frontend**
Next.js 15 (App Router) · TypeScript · Tailwind CSS v4 · shadcn/ui · Framer Motion · React Hook Form · Zod · Axios · TanStack Query · Lucide React · Recharts

**Backend**
Python · Django · Django REST Framework · Simple JWT · Pillow · django-filter · django-cors-headers

**Database**
PostgreSQL (via Django ORM)

**AI Modules** *(delivered independently, see [AI_MODULE_DELIVERY_SPECIFICATION.md](../docs/AI_MODULE_DELIVERY_SPECIFICATION.md))*
TensorFlow / PyTorch · OpenCV · Open-Meteo API

---

## 4. Project Architecture

```
Presentation Layer      → Next.js (this app)
Business Logic Layer    → Django REST Framework
AI Integration Layer    → Django service clients (never modifies AI responses)
AI Processing Modules   → Disease Detection · Soil & Nutrient Health · Weather Risk (→ Integrated Report)
Data Layer               → PostgreSQL (accessed only by the backend)
```

Rules enforced throughout the codebase:
- The frontend never calls AI services or the database directly — only `/api/v1/*` on the Django backend.
- The backend validates, stores, and forwards AI responses; it never recomputes predictions or renames JSON fields.
- Each module's result is shown as-is; nothing combines them into a final diagnosis.

Full detail: [`docs/GREEN_GUARD_SYSTEM_SPECIFICATION_V2.md`](../docs/GREEN_GUARD_SYSTEM_SPECIFICATION_V2.md).

---

## 5. Folder Structure

```
GreenGuard/
├── backend/                 Django project
│   ├── manage.py
│   ├── config/               settings, urls, wsgi/asgi
│   ├── requirements.txt
│   └── .env.example
│   # business apps (authentication, users, predictions, dashboard,
│   # notifications, adminpanel, ai_services, weather, common) are
│   # added incrementally per roadmap phase
│
├── frontend/                 Next.js project (this app)
│   ├── app/                  routes, layouts, pages
│   ├── components/           reusable UI (shadcn/ui in components/ui)
│   ├── features/             feature-scoped logic/components
│   ├── hooks/                 shared React hooks
│   ├── lib/                  api-client, utils
│   ├── providers/            theme + TanStack Query providers
│   ├── styles/                 additional stylesheets
│   ├── types/                 shared TypeScript types
│   ├── public/
│   └── .env.local.example
│
├── ai/                       reserved for the independently-delivered AI module package
├── docs/                     specifications (source of truth — see below)
├── CLAUDE.md                  development rules for this repository
└── README.md
```

---

## 6. Installation

**Prerequisites:** Python 3.11+, Node.js 20+, PostgreSQL 14+, Git.

```bash
git clone <repository-url>
cd GreenGuard
```

Then follow the **Running Backend** and **Running Frontend** sections below.

---

## 7. Environment Variables

**Backend** (`backend/.env`, copy from `backend/.env.example`):

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | Debug mode toggle |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts |
| `DATABASE_NAME` / `DATABASE_USER` / `DATABASE_PASSWORD` / `DATABASE_HOST` / `DATABASE_PORT` | PostgreSQL connection |
| `JWT_SECRET` | JWT signing key |
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` / `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | Token lifetimes |
| `CORS_ALLOWED_ORIGINS` | Allowed frontend origins |
| `ENABLE_MOCK_AI` | Serve fixture AI responses instead of calling real AI services |
| `DISEASE_MODULE_URL` / `GREENGUARD_API_KEY` / `STRESS_MODULE_URL` / `WEATHER_MODULE_URL` | AI module services (backend only) |

**Frontend** (`frontend/.env.local`, copy from `frontend/.env.local.example`):

| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Django backend base URL, e.g. `http://localhost:8000/api/v1` |
| `NEXT_PUBLIC_APP_NAME` | Display name |
| `NEXT_PUBLIC_ENVIRONMENT` | `development` / `production` |

Never commit `.env` or `.env.local`.

---

## 8. Running Backend

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash
# .venv\Scripts\activate.bat       # Windows cmd
# source .venv/bin/activate        # macOS/Linux

pip install -r requirements.txt
cp .env.example .env               # then fill in real DATABASE_* credentials

# create the PostgreSQL database/role for the values in .env, then:
python manage.py migrate
python manage.py runserver
```

Backend runs at `http://localhost:8000`.

---

## 9. Running Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Frontend runs at `http://localhost:3000`.

---

## 10. AI Module Integration Overview

GreenGuard integrates three independent AI modules, orchestrated **only** by the Django backend, plus an application-level report:

1. **Disease Detection** — disease from one leaf photo (top-3 shortlist; may report "uncertain").
2. **Soil & Nutrient Health** — nutrient risk and soil health score from a farmer questionnaire.
3. **Weather Risk** — fungal disease, heat stress, and drought risk via Open-Meteo, using the farm's stored coordinates.
4. **Integrated Analysis Report** — not an AI model: shows the results of modules 1–3 side by side, without combining them.

All request/response JSON contracts are frozen in [`docs/REST_API_SPEC.md`](../docs/REST_API_SPEC.md) and must never be renamed, restructured, or recomputed by the backend. While real AI endpoints are unavailable, the backend runs in **Mock Mode** (`ENABLE_MOCK_AI=True`) and returns fixture responses matching the exact contract shape, so frontend and backend development can proceed independently of AI delivery. Disabling Mock Mode requires no frontend changes.

---

## 11. Development Roadmap

Implementation strictly follows [`docs/PROJECT_IMPLEMENTATION_ROADMAP.md`](../docs/PROJECT_IMPLEMENTATION_ROADMAP.md), one phase at a time, with explicit approval required between phases:

- [x] **Phase 1** — Project Setup
- [ ] Phase 2 — Authentication Module
- [ ] Phase 3 — Farm Management Module
- [ ] Phase 4 — Dashboard Module
- [ ] Phase 5 — Weather Module
- [ ] Phase 6 — Plant Analysis Module
- [ ] Phase 7 — Prediction History Module
- [ ] Phase 8 — Notification Module
- [ ] Phase 9 — User Settings Module
- [ ] Phase 10 — AI Integration
- [ ] Phase 11 — Testing & Quality Assurance
- [ ] Phase 12 — Performance Optimization
- [ ] Phase 13 — Security
- [ ] Phase 14 — Deployment Preparation
- [ ] Phase 15 — Final Review

---

## 12. License

This project is developed as an academic Final Year Project (BS Computer Science) by Minahil Kamran, Laiba Farooq, and Hamia Khalil. All rights reserved by the authors unless a formal open-source license is added at a later date.
