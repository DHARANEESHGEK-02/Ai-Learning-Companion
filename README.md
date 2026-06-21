# AI Learning Companion — Industry-Grade Edition

A university-grade intelligent answer sheet evaluation platform powered by Google Gemini AI.

## Features

| Feature | Description |
|---|---|
| 🤖 AI Evaluation | Gemini-powered rubric-based scoring |
| 📝 OCR Processing | Extract text from handwritten PDFs & images |
| 📊 Semantic Scoring | Similarity analysis vs model answers |
| 🔍 Missing Concepts | Detects knowledge gaps in answers |
| 🎯 Personalized Plans | Auto-generated learning recommendations |
| 🤖 AI Tutor Chatbot | RAG-enhanced subject-specific tutoring |
| 📈 Analytics Dashboard | Performance trends & subject analytics |
| 🔒 Plagiarism Detection | TF-IDF cosine similarity detection |
| 📄 PDF/Excel Reports | Downloadable evaluation reports |
| 👨‍🏫 Faculty Dashboard | Batch evaluation & exam management |
| 👨‍🎓 Student Dashboard | Score history & learning plans |
| 🔐 Authentication | JWT-based role-based access control |

## Architecture

```
┌─────────────────────────┐     HTTP      ┌──────────────────────────┐
│   Streamlit Frontend    │ ─────────────▶ │   FastAPI Backend        │
│   (Port 5000)           │               │   (Port 8000)            │
│                         │               │                          │
│  • Login / Register     │               │  • Auth (JWT)            │
│  • Student Dashboard    │               │  • Exam Management       │
│  • Faculty Dashboard    │               │  • Answer Evaluation     │
│  • Upload & Evaluate    │               │  • Analytics API         │
│  • AI Tutor Chat        │               │  • Learning Plans        │
│  • Analytics            │               │                          │
│  • PDF/Excel Reports    │               └──────────┬───────────────┘
└─────────────────────────┘                          │
                                                     ▼
                                          ┌──────────────────────┐
                                          │   PostgreSQL DB       │
                                          │                      │
                                          │  users, exams,       │
                                          │  questions,          │
                                          │  answer_sheets,      │
                                          │  evaluations,        │
                                          │  learning_plans,     │
                                          │  chat_messages       │
                                          └──────────────────────┘
                                                     │
                                                     ▼
                                          ┌──────────────────────┐
                                          │   Google Gemini API   │
                                          │                      │
                                          │  • Vision OCR        │
                                          │  • Answer Evaluation │
                                          │  • AI Tutoring       │
                                          │  • Embeddings (RAG)  │
                                          └──────────────────────┘
```

## Evaluation Pipeline

```
Student Upload (PDF/Image/Text)
    ↓
Gemini Vision OCR Extraction
    ↓
Question Segmentation
    ↓
Rubric-Based Scoring (Gemini)
    ↓
Semantic Similarity Analysis
    ↓
Missing Concept Detection
    ↓
Plagiarism Check (TF-IDF)
    ↓
Personalized Feedback Generation
    ↓
Learning Plan Generation
    ↓
PDF/Excel Report
```

## Quick Start (Replit)

The app runs automatically. Two workflows are configured:
- **Start application** — Streamlit frontend on port 5000
- **Backend API** — FastAPI on port 8000

## Quick Start (Docker)

```bash
# Clone and configure
cp .env.example .env
# Edit .env with your GEMINI_API_KEY and DATABASE_URL

# Run with Docker Compose
docker-compose up --build

# Access
# Frontend: http://localhost:5000
# Backend API docs: http://localhost:8000/docs
```

## Environment Variables

| Variable | Description | Required |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | ✅ |
| `GEMINI_API_KEY` | Google Gemini API key | ✅ |
| `SESSION_SECRET` | JWT signing secret | ✅ |

## API Documentation

FastAPI auto-generates interactive API docs at `/docs` (Swagger UI) and `/redoc`.

## Subjects Supported

- **Computer Science** — Algorithms, data structures, code logic
- **Physics** — Formulas, derivations, numerical accuracy
- **Chemistry** — Equations, reactions, mechanisms
- **Biology** — Processes, classifications, terminology
- **Mathematics** — Proofs, calculations, formula application

## Roles

| Role | Capabilities |
|---|---|
| **Student** | Submit answer sheets, view scores, chat with AI tutor, download personal reports |
| **Faculty** | Create exams, add questions with rubrics, batch evaluate, view all submissions, analytics, batch reports |

## Tech Stack

- **Frontend**: Streamlit 1.41
- **Backend**: FastAPI 0.115 + Uvicorn
- **Database**: PostgreSQL + SQLAlchemy 2.0
- **AI**: Google Gemini 1.5 Flash (Vision + Text + Embeddings)
- **Auth**: JWT (python-jose) + bcrypt (passlib)
- **Reports**: ReportLab (PDF) + openpyxl (Excel)
- **Plagiarism**: TF-IDF Cosine Similarity
- **Containerization**: Docker + Docker Compose
