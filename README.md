# CareerAI — Intelligent Career Companion

An end-to-end, AI-powered career platform designed for students and job seekers. CareerAI brings together an intelligent voice mock interview, real-time ATS resume building and optimization, smart score analysis, and automated job matching.

---

## Architecture Overview

This repository represents the unified, production-ready CareerAI codebase:
* **`Frontend/`** — Redesigned, user-centric interface featuring a signature Dark Red (`#681313`) and Warm Cream (`#FFF9EF`) design system, interactive CarA mascot animations, dynamic SVG score gauges, and responsive multi-tool workflows.
* **`backend/`** — High-performance FastAPI application powered by SQLAlchemy ORM, PostgreSQL, Alembic database migrations, and Google Gemini SDK.
* **`smart_hiring/`** — Job catalog and fallback recommendations database.
* **`resume_interview.py`** — Interactive AI interview state machine.

---

## Key Features

1. **AI Voice Mock Interview (`interview.html`)**
   * Real-time audio recording and speech-to-text transcription.
   * Dynamic, role-targeted interview questions adapted to candidate responses.
   * Automatic career aspiration and qualification profile synthesis.
2. **Resume Optimizer & Builder (`resume.html`, `optimize.html`)**
   * Proportional 25% – 75% interactive preview canvas.
   * Real-time ATS formatting recommendations and instant PDF export.
3. **ATS Score Checker (`ats.html`)**
   * PDF resume upload and Gemini-powered structural extraction.
   * Animated semicircle ATS score gauge (0–100 scale).
   * Detailed breakdown of keyword matches, missing qualifications, and section corrections.
4. **Smart Job Matcher (`jobs.html`)**
   * Real-time job listings retrieved from PostgreSQL or local catalogs.
   * AI candidate-to-job matching evaluating fit, matched skills, and actionable suggestions.
   * Application status tracking.
5. **Profile & Synchronized Analytics (`profile.html`, `dashboard.html`)**
   * Centralized hub tracking resumes made, ATS scores, and saved job applications.

---

## Local Development Setup

### 1. Clone the Repository
```bash
git clone https://github.com/ananya-vishal-walunjkar07/fep.git
cd fep
```

### 2. Set Up Python Virtual Environment
```bash
# Create a virtual environment
python -m venv .venv

# Activate on Windows (PowerShell):
.\.venv\Scripts\activate

# Activate on macOS/Linux:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 4. Configure Environment Variables
Copy the template to create your local `.env`:
```bash
cp backend/.env.example backend/.env
```
Open `backend/.env` and supply your credentials:
```env
# Database (PostgreSQL / Supabase / Neon / Render)
DATABASE_URL=postgresql://user:password@host:5432/database_name

# Security
JWT_SECRET=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_API_KEY2=your_optional_second_key_here
GEMINI_MODEL=gemini-3.8-flash
GEMINI_FALLBACK_MODEL=gemini-3.1-flash-lite
```

### 5. Run Database Migrations
To create all database tables (`users`, `resumes`, `reports`, `jobs`, `applications`):
```bash
cd backend
alembic upgrade head
cd ..
```

### 6. Start the Application
Run the backend server:
```bash
uvicorn main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```
* **API Server:** `http://127.0.0.1:8000`
* **Swagger Documentation:** `http://127.0.0.1:8000/docs`
* **Health Check:** `http://127.0.0.1:8000/health`

In a separate terminal, start the frontend:
```bash
cd Frontend
python -m http.server 5500
```
Open **`http://127.0.0.1:5500/landing.html`** in your browser.

---

## Render Deployment Guide

You can deploy CareerAI on [Render](https://render.com) using either of the two standard workflows:

### Option A: Decoupled Deployment (Recommended)

#### Step 1: Deploy PostgreSQL Database on Render
1. Log in to Render Dashboard $\rightarrow$ Click **New +** $\rightarrow$ **PostgreSQL**.
2. Name: `careerai-db`.
3. Plan: Free.
4. Copy the **Internal Database URL** (or External Database URL if deploying outside Render).

#### Step 2: Deploy Backend Web Service
1. In Render Dashboard $\rightarrow$ Click **New +** $\rightarrow$ **Web Service**.
2. Connect your GitHub repository: `ananya-vishal-walunjkar07/fep`.
3. Configure settings:
   * **Name:** `careerai-backend`
   * **Root Directory:** `backend`
   * **Environment:** `Python 3`
   * **Build Command:** `pip install -r requirements.txt && alembic upgrade head`
   * **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. In the **Environment Variables** section, add:
   * `DATABASE_URL` = *(Your Render PostgreSQL URL or Supabase connection string)*
   * `JWT_SECRET` = *(Generate a random 32-character secret)*
   * `JWT_ALGORITHM` = `HS256`
   * `ACCESS_TOKEN_EXPIRE_MINUTES` = `60`
   * `GEMINI_API_KEY` = *(Your Google Gemini API key)*
   * `GEMINI_MODEL` = `gemini-3.8-flash`
   * `GEMINI_FALLBACK_MODEL` = `gemini-3.1-flash-lite`
   * `CORS_ORIGINS` = `https://your-frontend-app.onrender.com`
5. Click **Create Web Service**. Note your backend URL (e.g., `https://careerai-backend.onrender.com`).

#### Step 3: Deploy Frontend as a Static Site
1. In Render Dashboard $\rightarrow$ Click **New +** $\rightarrow$ **Static Site**.
2. Connect `ananya-vishal-walunjkar07/fep`.
3. Configure settings:
   * **Name:** `careerai-frontend`
   * **Publish Directory:** `Frontend`
4. In `Frontend/api.js`, set `window.CAREERAI_API_BASE` or update `API_BASE` to your backend URL:
   ```javascript
   const API_BASE = window.CAREERAI_API_BASE || "https://careerai-backend.onrender.com";
   ```
5. Deploy and visit your live CareerAI URL!

---

## Security & Secrets
* No credentials, passwords, or API keys are stored in this repository.
* All environment variables are loaded dynamically from `.env` locally or via the hosting platform's secure environment settings in production.
* Local `.env` files are strictly excluded from version control via `.gitignore`.
