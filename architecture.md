# Architecture — KYC Extraction Pipeline

## Overview

The KYC Extraction Pipeline is a self-hosted, offline-capable document intelligence system. It accepts image or PDF uploads of KYC documents (Aadhaar, PAN, Passport), extracts structured identity fields using a multi-stage OCR and NLP pipeline, validates the extracted data, and returns structured JSON results with field-level confidence scores.

The system is designed around three principles:

- **Zero cloud dependency** — no external OCR APIs, no cloud storage, no UIDAI calls. All processing happens on-premise.
- **Async by default** — document processing is decoupled from the HTTP request lifecycle via a task queue. Upload returns immediately; clients poll for results.
- **Observable** — every job is tracked in PostgreSQL with full audit logs. Prometheus scrapes API metrics. Grafana visualises throughput, latency, and error rates.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        Client                           │
│              HTML + Tailwind frontend                   │
│           (live status polling via GET /status)         │
└─────────────────────┬───────────────────────────────────┘
                      │ POST /upload
                      ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Gateway                       │
│         Validates file · Creates job record             │
│         Stores file in MinIO · Queues Celery task        │
└──────┬──────────────────────┬───────────────────────────┘
       │                      │
       ▼                      ▼
┌─────────────┐     ┌──────────────────┐     ┌───────────┐
│ PostgreSQL  │     │      Redis       │     │   MinIO   │
│  job record │     │   task queue     │     │  raw file │
│  audit log  │     │   broker         │     │  storage  │
└─────────────┘     └────────┬─────────┘     └───────────┘
                             │ dequeue
                             ▼
┌─────────────────────────────────────────────────────────┐
│                    Celery Worker                        │
│                                                         │
│   OpenCV preprocessing                                  │
│        │                                                │
│        ▼                                                │
│   Tesseract OCR  (eng+hin, PSM 6, OEM 3)               │
│        │                                                │
│        ▼                                                │
│   spaCy + Regex field extractor                         │
│        │                                                │
│        ▼                                                │
│   Verhoeff UID validator                                │
│        │                                                │
│        ▼                                                │
│   Write results → PostgreSQL                            │
└─────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│                    Monitoring                           │
│        Prometheus (scrapes /metrics every 10s)          │
│        Grafana (dashboards, alerting)                   │
└─────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. FastAPI Gateway (`api/main.py`)

The HTTP entry point. Handles all inbound requests and orchestrates the upload flow.

**Responsibilities:**
- File validation — extension whitelist (`.jpg`, `.jpeg`, `.png`, `.pdf`), 8MB size cap
- UUID job ID generation — each upload gets a unique `job_id` used as the primary key throughout the system
- Local file persistence — saves to `uploads/{job_id}.{ext}` for the Celery worker to read
- MinIO upload — stores a permanent copy in object storage with the path `kyc-documents/{job_id}.{ext}`
- PostgreSQL record creation — writes initial `pending` status job and audit log entry
- Celery task dispatch — fires `process_document.apply_async(args=[job_id, file_path])`
- Status polling endpoint — `GET /status/{job_id}` reads job state from PostgreSQL

**Key design decision — why local disk AND MinIO?**
Celery reads the file from local disk for OCR processing (fast, no network overhead). MinIO is the permanent store — if the local `uploads/` folder is cleaned or the container restarts, the original document is not lost. The MinIO URL is stored in PostgreSQL alongside the extraction results.

**Endpoints:**

| Method | Path | Description |
|---|---|---|
| POST | `/upload` | Upload document, returns `job_id` |
| GET | `/status/{job_id}` | Poll extraction result |
| GET | `/jobs` | List all jobs (paginated) |
| GET | `/jobs/review` | Jobs with confidence < 85% |
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |

---

### 2. Task Queue — Redis + Celery (`workers/celery_app.py`, `workers/tasks.py`)

Decouples the HTTP upload from the processing pipeline. The upload endpoint returns in milliseconds; processing happens asynchronously.

**Redis** acts as the message broker. When FastAPI calls `process_document.apply_async()`, a message is written to the Redis queue with the `job_id` and `file_path` as arguments.

**Celery** worker pulls messages from Redis and executes the `process_document` task. Configured with `--pool=solo` on Windows (default multiprocessing pool is incompatible with Windows fork behaviour). In the Docker environment, this is irrelevant — the container runs Linux.

**Retry policy:** `max_retries=3`, `countdown=5` seconds. If the task raises an exception (OCR failure, DB connection drop), Celery automatically retries up to 3 times before marking the job as failed.

**Task flow:**
```
process_document(job_id, file_path)
  → update_job_processing()       # status: pending → processing
  → extract_text(file_path)       # OCR pipeline
  → extract_fields(raw_text)      # NLP extraction
  → update_job_completed()        # writes fields, confidence, validation
  → create_audit_log("completed") # audit trail
```

---

### 3. OCR Pipeline

Three sequential stages, each transforming the document into increasingly structured data.

#### Stage 1 — OpenCV Preprocessing (`workers/preprocessor.py`)

Raw document images contain noise, skew, and lighting variation that degrades OCR accuracy. OpenCV preprocessing normalises the image before Tesseract sees it.

**Operations applied:**
- Grayscale conversion — reduces colour noise
- Gaussian blur — smooths high-frequency noise while preserving edges
- Adaptive thresholding — handles uneven lighting across the document (common in phone-captured Aadhaar cards)
- Deskewing — corrects rotation artifacts from non-flat scanning

**Why adaptive thresholding over global thresholding?**
Global thresholding applies a single pixel intensity cutoff across the entire image. On a document photographed under uneven light (shadow on one side, bright on the other), this produces binary artifacts. Adaptive thresholding computes the threshold locally per region, preserving text in both bright and shadow areas.

#### Stage 2 — Tesseract OCR (`workers/ocr_engine.py`)

Extracts raw text from the preprocessed image.

**Configuration:**
```python
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
config = "--psm 6 --oem 3"
lang = "eng+hin"
```

**PSM 6** — "Assume a single uniform block of text." Appropriate for structured identity documents where text is laid out in consistent blocks. PSM 3 (fully automatic) introduces unnecessary segmentation overhead and can split fields incorrectly on card layouts.

**OEM 3** — Uses both LSTM neural network engine and legacy engine, with LSTM preferred. LSTM engine produces significantly better accuracy on printed document text.

**eng+hin** — Aadhaar cards contain Hindi text (name, address, and state fields) alongside English. Using only `eng` drops all Hindi field content. The combined model handles bilingual cards.

#### Stage 3 — spaCy + Regex Field Extractor (`workers/regex_extractor.py`)

Takes raw OCR text and extracts structured fields with confidence scores.

**Approach — why regex over pure NLP?**
KYC documents have highly predictable formats. Aadhaar UIDs are always 12 digits. PAN numbers always follow `[A-Z]{5}[0-9]{4}[A-Z]{1}`. Passport MRZ lines have fixed-width fields. Regex patterns for these are more reliable and faster than NER models trained on general text.

spaCy (`en_core_web_sm`) handles fields with variable formats — names, addresses — where pattern matching alone is insufficient. Named entity recognition identifies PERSON and GPE (geopolitical entity) entities from the OCR text, which are then mapped to `name` and `address` fields.

**Confidence scoring:**
Each extracted field gets a confidence score (0.0–1.0) based on:
- Pattern match quality — exact regex match = high confidence, partial = lower
- Character confidence from Tesseract (`image_to_data` output) — averaged over the field's bounding region
- Field presence — expected fields that are absent are scored 0.0

`overall_confidence` = weighted average across all fields. Jobs with `overall_confidence < 0.85` are flagged for human review via `GET /jobs/review`.

---

### 4. Verhoeff Validator (`workers/validators.py`)

Validates Aadhaar UIDs offline without calling UIDAI's API.

**What is the Verhoeff algorithm?**
A checksum algorithm based on the dihedral group D5. Unlike Luhn (used by credit cards), Verhoeff catches all single-digit errors and all adjacent transposition errors — the two most common human data entry mistakes.

**Why not Luhn?**
Luhn is a simpler mod-10 checksum. It catches all single-digit errors but misses some transpositions (specifically, swapping 0 and 9). UIDAI chose Verhoeff because Aadhaar UIDs are 12 digits entered manually, and transposition errors are common in manual transcription.

**Implementation:**
Three lookup tables — multiplication table, permutation table, inverse table — derived from the dihedral group D5. Validation runs in O(n) time over the 12-digit UID.

```python
def validate(number: str) -> bool:
    c = 0
    for i, digit in enumerate(reversed(number)):
        c = MULT_TABLE[c][PERM_TABLE[i % 8][int(digit)]]
    return c == 0
```

A valid UID produces `c == 0`. Invalid UIDs (including random 12-digit numbers) almost never pass — the false positive rate is 1/10.

---

### 5. PostgreSQL — Data Layer (`api/models.py`, `api/db_operations.py`)

Two tables: `extraction_jobs` and `audit_logs`.

**`extraction_jobs` schema:**

| Column | Type | Description |
|---|---|---|
| `job_id` | VARCHAR (PK) | UUID, primary key |
| `status` | VARCHAR | `pending` → `processing` → `completed` / `failed` |
| `document_type` | VARCHAR | `aadhaar`, `pan`, `passport`, `unknown` |
| `file_path` | VARCHAR | Local disk path |
| `minio_url` | VARCHAR | `minio://kyc-documents/{job_id}.ext` |
| `fields` | JSONB | Extracted field values and per-field confidence |
| `validation` | JSONB | Verhoeff and format validation results |
| `overall_confidence` | FLOAT | Weighted confidence score |
| `error_message` | TEXT | Set on failure |
| `created_at` | TIMESTAMPTZ | Auto-set on insert |
| `completed_at` | TIMESTAMPTZ | Set on completion or failure |
| `manually_reviewed` | BOOLEAN | Set by human reviewer |

**`audit_logs` schema:**

| Column | Type | Description |
|---|---|---|
| `id` | VARCHAR (PK) | UUID |
| `job_id` | VARCHAR | References extraction_jobs |
| `action` | VARCHAR | `uploaded`, `processing`, `completed`, `failed` |
| `details` | JSONB | Contextual metadata (filename, confidence, error) |
| `timestamp` | TIMESTAMPTZ | Auto-set on insert |

**Why JSONB for `fields` and `validation`?**
Document types have different field schemas — Aadhaar has a UID, PAN has a PAN number, Passport has MRZ fields. JSONB allows a single table to store heterogeneous field structures without requiring per-document-type tables or nullable columns for every possible field.

---

### 6. MinIO Object Storage (`api/minio_client.py`)

S3-compatible object storage running locally. All uploaded documents are stored at `kyc-documents/{job_id}.{ext}`.

**Why MinIO over local filesystem only?**
- Documents survive container restarts (persisted volume)
- S3-compatible API — the same code works against AWS S3 in a production deployment by changing the endpoint URL and credentials
- Bucket-level access control and retention policies are available without code changes
- Provides a management console (port 9001) for direct file inspection

**Bucket creation:** `ensure_bucket()` is called on every upload. It checks if `kyc-documents` exists and creates it if not. This is idempotent — safe to call repeatedly.

---

### 7. Monitoring — Prometheus + Grafana

**Prometheus** scrapes `/metrics` every 10 seconds. The `/metrics` endpoint is exposed by `prometheus-fastapi-instrumentator`, which automatically tracks:
- HTTP request count by endpoint and status code
- Request latency (p50, p95, p99) by endpoint
- In-progress requests

**Grafana** connects to Prometheus as a data source. Key panels to build:
- Request rate — `rate(http_requests_total[1m])`
- p95 latency — `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`
- Error rate — `rate(http_requests_total{status=~"5.."}[1m])`
- Job completion rate — query PostgreSQL directly via Grafana PostgreSQL datasource

---

## Data Flow — End to End

```
1. Client uploads document via POST /upload

2. FastAPI:
   a. Validates file (extension, size)
   b. Generates job_id (UUID)
   c. Saves file to uploads/{job_id}.ext
   d. Uploads to MinIO → stores minio_url
   e. Creates PostgreSQL job record (status: pending)
   f. Creates audit log entry (action: uploaded)
   g. Fires Celery task: process_document(job_id, file_path)
   h. Returns {job_id, status: pending} to client

3. Client polls GET /status/{job_id} every 2 seconds

4. Celery worker:
   a. Picks up task from Redis queue
   b. Updates job status → processing
   c. OpenCV: grayscale → blur → adaptive threshold → deskew
   d. Tesseract: extract raw text (eng+hin, PSM 6, OEM 3)
   e. spaCy + Regex: extract fields + confidence scores
   f. Verhoeff: validate Aadhaar UID if present
   g. Updates job status → completed, writes fields + confidence
   h. Creates audit log entry (action: completed)

5. Client receives completed status with structured JSON fields

6. If overall_confidence < 0.85:
   → Job appears in GET /jobs/review for human review
```

---

## Docker Compose Services

| Service | Image | Port | Purpose |
|---|---|---|---|
| `api` | Built from Dockerfile | 8000 | FastAPI + Uvicorn |
| `celery` | Built from Dockerfile | — | Celery worker |
| `postgres` | postgres:15-alpine | 5432 | Job storage |
| `redis` | redis:7-alpine | 6379 | Task broker |
| `minio` | minio/minio | 9000, 9001 | Object storage + console |
| `prometheus` | prom/prometheus | 9090 | Metrics collection |
| `grafana` | grafana/grafana | 3000 | Metrics visualisation |

**Startup order:** Redis and PostgreSQL must be healthy before the API and Celery containers start. MinIO must be healthy before the API starts. This is enforced via `depends_on` with `condition: service_healthy` and Docker healthchecks on each infrastructure service.

---

## Key Technical Decisions

| Decision | Choice | Rationale |
|---|---|---|
| OCR engine | Tesseract | Open-source, supports Hindi (eng+hin), no API cost, runs offline |
| Task queue | Celery + Redis | Industry standard, supports retries, works with FastAPI without blocking |
| UID validation | Verhoeff | UIDAI's actual algorithm — catches transpositions Luhn misses |
| Document storage | MinIO | S3-compatible, self-hosted, survives container restarts |
| Field extraction | Regex + spaCy | Regex for structured fields (UID, PAN), NER for unstructured (name, address) |
| OCR config | PSM 6, OEM 3 | PSM 6 optimal for card-layout documents; OEM 3 uses LSTM engine |
| DB field schema | JSONB | Heterogeneous field schemas across document types without schema migration per type |
| Windows Celery | `--pool=solo` | Default multiprocessing pool incompatible with Windows fork model |

---

## Limitations & Known Gaps

- **Handwritten documents** — Tesseract is trained on printed text. Handwritten Aadhaar fields (rare, but exist in older cards) will produce poor OCR output.
- **Heavily damaged/folded documents** — Preprocessing handles minor noise but cannot reconstruct severely damaged documents.
- **PAN + Passport validation** — Verhoeff is implemented for Aadhaar only. PAN format validation is regex-based. Passport MRZ checksum validation is not yet implemented.
- **No authentication** — The API has no auth layer. In a production deployment, JWT-based auth or API key middleware should be added before the upload endpoint.
- **Local file cleanup** — Processed files accumulate in `uploads/`. A scheduled cleanup job (e.g., delete files older than 24 hours) is not yet implemented.
- **Single Celery worker** — The current setup runs one worker. For higher throughput, horizontal scaling via multiple Celery workers with a shared Redis broker is straightforward to add.
