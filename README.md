# KYC Extraction Pipeline

A self-hosted, offline-capable KYC document extraction system for Aadhaar, PAN, and Passport documents. Extracts structured fields in under 2 seconds with field-level confidence scoring. Zero cloud dependency — sensitive data stays on-premise.

---

## Problem

Indian businesses spend 15–30 minutes per customer on manual KYC data entry with 3–8% human error rates. Third-party KYC APIs cost ₹5–15 per document and introduce data privacy risks by sending sensitive documents to external servers.

## Solution

A fully self-hosted pipeline that processes KYC documents entirely offline using open-source tooling. One command starts the entire stack.

---

## Tech Stack

| Layer | Technology |
|---|---|
| API Gateway | FastAPI + Uvicorn |
| Task Queue | Celery + Redis |
| OCR | Tesseract (eng+hin) + OpenCV |
| Field Extraction | spaCy + Regex |
| UID Validation | Verhoeff Algorithm |
| Database | PostgreSQL |
| Document Storage | MinIO (S3-compatible) |
| Monitoring | Prometheus + Grafana |
| Containerisation | Docker Compose |

---

## Architecture

```
Upload (HTTP)
     │
     ▼
FastAPI Gateway ──► PostgreSQL (job record)
     │               MinIO (file storage)
     ▼
Redis Queue
     │
     ▼
Celery Worker
     │
     ├── OpenCV (preprocessing)
     ├── Tesseract OCR (text extraction)
     ├── spaCy + Regex (field parsing)
     └── Verhoeff (UID validation)
     │
     ▼
PostgreSQL (results)
     │
     ▼
GET /status/{job_id} → JSON response
```

---

## Project Structure

```
kyc-extraction-pipeline/
├── api/
│   ├── main.py              # FastAPI app, endpoints
│   ├── schemas.py           # Pydantic models
│   ├── database.py          # SQLAlchemy connection
│   ├── models.py            # PostgreSQL table definitions
│   ├── db_operations.py     # CRUD operations
│   └── minio_client.py      # MinIO upload helper
├── workers/
│   ├── celery_app.py        # Celery configuration
│   ├── tasks.py             # Async task definitions
│   ├── preprocessor.py      # OpenCV preprocessing
│   ├── ocr_engine.py        # Tesseract OCR
│   ├── regex_extractor.py   # Field extraction
│   └── validators.py        # Verhoeff UID validation
├── frontend/
│   └── index.html           # Upload UI with live polling
├── prometheus.yml           # Prometheus scrape config
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Quick Start

**Prerequisites:** Docker Desktop running on your machine. That's it.

```bash
git clone https://github.com/BharadwajVarun/kyc-extraction-pipeline.git
cd kyc-extraction-pipeline
docker compose up --build
```

First build takes 3–5 minutes (downloads Python image, installs Tesseract + spaCy model). Subsequent starts are fast.

**Services started:**

| Service | URL |
|---|---|
| API (Swagger docs) | http://localhost:8000/docs |
| Frontend | http://localhost:8000 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |
| MinIO Console | http://localhost:9001 |

Grafana login: `admin` / `admin`

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/upload` | Upload a KYC document |
| GET | `/status/{job_id}` | Poll extraction status and results |
| GET | `/jobs` | List all extraction jobs |
| GET | `/jobs/review` | Jobs with confidence < 85% |
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |

### Example response — `/status/{job_id}`

```json
{
  "job_id": "557449c1-d3a5-46e1-a3b3-06814ce003f5",
  "status": "completed",
  "document_type": "aadhaar",
  "fields": {
    "aadhaar_uid": { "value": "2167 6218 9564" },
    "name": { "value": "Varun Bharadwaj" },
    "date_of_birth": { "value": "01/01/1999" },
    "gender": { "value": "Male" }
  },
  "validation": {
    "aadhaar_uid": true
  },
  "overall_confidence": 0.92
}
```

---

## Key Technical Decisions

**Verhoeff Algorithm for offline UID validation**
Aadhaar UIDs use the Verhoeff checksum — a dihedral group-based algorithm that catches transposition errors regular checksums miss. Validation runs entirely offline without calling UIDAI's API.

→ Full writeup: [How I validated Aadhaar UIDs offline without calling UIDAI's API](https://medium.com/@bvarun855)

**Celery with `--pool=solo` on Windows**
Default multiprocessing pool doesn't work on Windows. Solo pool runs tasks in the main process — identical behaviour for single-worker deployments.

**OCR language: `eng+hin`**
Aadhaar cards contain Hindi text alongside English. Tesseract's combined language model improves field extraction accuracy on bilingual documents.

**MinIO for document storage**
S3-compatible object storage running locally. Documents are stored as `{job_id}.{ext}` with the MinIO URL saved in PostgreSQL alongside extraction results.

---

## Supported Documents

| Document | Fields Extracted |
|---|---|
| Aadhaar | UID, Name, DOB, Gender, Address |
| PAN | PAN Number, Name, DOB, Father's Name |
| Passport | Passport Number, Name, DOB, Nationality, MRZ |

---

## Build Log

Built and documented publicly on LinkedIn, post by post.

[linkedin.com/in/varunbharadwaj](https://www.linkedin.com/in/varunbharadwaj)

---

## Author

**Varun Bharadwaj**
B.E. AI & Data Science, VTU Bengaluru — 2025
[Portfolio](https://portfolio-pi-swart-tuos89wqp3.vercel.app) · [LinkedIn](https://www.linkedin.com/in/varunbharadwaj) · [GitHub](https://github.com/BharadwajVarun)