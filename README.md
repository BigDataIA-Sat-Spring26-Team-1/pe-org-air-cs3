# PE Org-AI-R Platform 🚀
> **Enterprise-Grade Intelligence Engine for Private Equity AI Due Diligence**

![Next.js](https://img.shields.io/badge/Next.js-15-black?style=for-the-badge&logo=next.js)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-05998b?style=for-the-badge&logo=fastapi)
![Snowflake](https://img.shields.io/badge/Snowflake-Data_Cloud-29B5E8?style=for-the-badge&logo=snowflake)
![Redis](https://img.shields.io/badge/Redis-Caching-DC382D?style=for-the-badge&logo=redis)
![Airflow](https://img.shields.io/badge/Airflow-Orchestration-017CEE?style=for-the-badge&logo=apacheairflow)
![Playwright](https://img.shields.io/badge/Playwright-Automation-2EAD33?style=for-the-badge&logo=playwright)
![Docker](https://img.shields.io/badge/Docker-Orchestration-2496ED?style=for-the-badge&logo=docker)

The **PE Org-AI-R Platform** is a sophisticated data orchestration and analytics platform engineered to help Private Equity firms assess the technological maturity and AI readiness of target portfolio companies. The system automates the capture of high-fidelity signals from SEC filings, global patent registries, technology job markets, and **Glassdoor employee reviews** to compute a multi-dimensional AI-readiness score.

---

## 🛠 Technology Stack & Core Dependencies

| Layer | Technologies & Frameworks |
| :--- | :--- |
| **Frontend** | ![Next.js](https://img.shields.io/badge/Next.js-000?style=flat&logo=next.js&logoColor=white) **Next.js 15 (App Router)**, **TypeScript**, **Tailwind CSS**, **Lucide React** |
| **Backend** | ![FastAPI](https://img.shields.io/badge/FastAPI-05998b?style=flat&logo=fastapi&logoColor=white) **FastAPI**, **Pydantic V2**, **Structured Logging (structlog)**, **Tenacity (Retry Logic)** |
| **Data & Cache** | ![Snowflake](https://img.shields.io/badge/Snowflake-29B5E8?style=flat&logo=snowflake&logoColor=white) **Snowflake (SQL Alchemy + Snowflake-connector)**, ![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat&logo=redis&logoColor=white) **Redis (aioredis)** |
| **Orchestration** | ![Airflow](https://img.shields.io/badge/Airflow-017CEE?style=flat&logo=apacheairflow&logoColor=white) **Apache Airflow 2.x** (TaskFlow API, Dynamic Task Mapping) |
| **Pipelines** | ![Playwright](https://img.shields.io/badge/Playwright-2EAD33?style=flat&logo=playwright&logoColor=white) **Playwright (Stealth Mode)**, **JobSpy (LinkedIn Scraper)**, **Wextractor (Glassdoor API)**, **Boto3 (AWS S3)** |
| **Testing** | ![Pytest](https://img.shields.io/badge/Pytest-0A9EDC?style=flat&logo=pytest&logoColor=white) **Pytest**, **Asyncio In-Memory Testing** |

---

## 📚 Documentation & Resources
*   **Codelabs Guide**: [Detailed Step-by-Step Walkthrough](https://codelabs-preview.appspot.com/?file_id=1z3QNIXveTzj0-KyBfuS46IGHTSKYBC2cAkpQrPN1ALQ#0)
*   **Codelab Documentation**: [Project Technical Manual](https://docs.google.com/document/d/1z3QNIXveTzj0-KyBfuS46IGHTSKYBC2cAkpQrPN1ALQ/edit?tab=t.0)
*   **Architecture Diagram**:
    ![Architecture Diagram](./pe-org-air-platform/Architecture_Diagram.jpeg)
*   **Video Demonstration**: [Full Platform Walkthrough](https://drive.google.com/file/d/1KJ-JuXoVbiEB0IHeeLY3EPvKNikRtyoZ/view?usp=sharing)

---

## 📂 Project Structure
```text
.
  |docker
  |--|Dockerfile
  |--|docker-compose.yml
  |--|dags/                          # Airflow DAG mount point
  |--|logs/                          # Airflow log volume
  |--|plugins/                       # Airflow plugins mount
  |dags
  |--|integration_pipeline_dag.py    # Full scoring pipeline (daily)
  |--|sec_ingestion_dag.py           # SEC filing ingestion (daily)
  |--|sec_backfill_dag.py            # SEC backfill (manual trigger)
  |--|sec_monitor_dag.py             # SEC data quality audit (weekly)
  |app
  |--|routers
  |--|--|metrics.py
  |--|--|signals.py
  |--|--|routers_utils.py
  |--|--|config.py
  |--|--|health.py
  |--|--|__init__.py
  |--|--|sec.py
  |--|--|companies.py
  |--|--|testing.py
  |--|--|assessments.py
  |--|--|evidence.py
  |--|--|industries.py
  |--|--|integration.py               # Integration pipeline trigger
  |--|database
  |--|--|seed.sql
  |--|--|schema.sql
  |--|--|schema_sec.sql
  |--|--|schema_signal.sql
  |--|--|schema_culture.sql           # Glassdoor culture scores
  |--|--|__init__.py
  |--|config.py
  |--|__init__.py
  |--|pipelines
  |--|--|integration_pipeline.py      # Master integration orchestrator
  |--|--|board_analyzer.py            # Board composition analyzer
  |--|--|sec
  |--|--|--|pipeline.py
  |--|--|--|downloader.py
  |--|--|--|parser.py
  |--|--|--|chunker.py
  |--|--|--|components.py             # Airflow-compatible task components
  |--|--|glassdoor
  |--|--|--|glassdoor_collector.py     # Review fetcher & rubric scorer
  |--|--|--|glassdoor_orchestrator.py  # Batch orchestration & persistence
  |--|--|--|glassdoor_queries.py       # Snowflake query templates
  |--|--|external_signals
  |--|--|--|orchestrator.py
  |--|--|--|job_collector.py
  |--|--|--|patent_collector.py
  |--|--|--|tech_stack_collector.py
  |--|--|--|leadership_collector.py
  |--|--|--|utils.py
  |--|logging_conf.py
  |--|models
  |--|--|assessment.py
  |--|--|signals.py
  |--|--|enums.py
  |--|--|company.py
  |--|--|registry.py
  |--|--|__init__.py
  |--|--|common.py
  |--|--|sec.py
  |--|--|industry.py
  |--|--|dimension.py
  |--|--|scoring.py                   # Scoring result models
  |--|--|glassdoor_models.py          # Glassdoor review models
  |--|--|board.py                     # Board composition models
  |--|scoring                         # AI Readiness Scoring Engine
  |--|--|rubric_scorer.py             # Rubric-based scoring logic
  |--|--|calculators.py               # VR, HR, Synergy, Confidence, OrgAIR
  |--|--|evidence_mapper.py           # Signal → Dimension evidence mapping
  |--|--|talent_analyzer.py           # Talent concentration analysis
  |--|--|position_factor.py           # Position-factor calculator
  |--|--|utils.py
  |--|main.py
  |--|services
  |--|--|__init__.py
  |--|--|backfill.py
  |--|--|snowflake.py
  |--|--|s3_storage.py
  |--|--|redis_cache.py
  |--|--|sector_config.py             # Sector/industry configuration
  |pytest.ini
  |frontend
  |--|postcss.config.mjs
  |--|Dockerfile
  |--|README.md
  |--|public
  |--|package.json
  |--|tsconfig.json
  |--|next.config.ts
  |--|src
  |--|--|app
  |requirements.txt
  |pyproject.toml
  |tests
  |--|test_concurrency.py
  |--|conftest.py
  |--|test_performance_cache.py
  |--|test_flows.py
  |--|test_sec_downloader.py
  |--|test_models.py
  |--|test_api.py
  |--|test_scoring_properties.py      # Scoring engine property tests
  |README.md
  |logs
  |--|app.log
  |data
  |--|sec_downloads
  |--|README.md
```

---

## 🚀 Deployment & Installation

### 1. Requirements & Prerequisites
*   **Docker Desktop** (with Compose V2)
*   **Snowflake Account** (With `ACCOUNTADMIN` or equivalent to create tables)
*   **AWS S3 Bucket** (Optional: for unstructured filing storage)
*   **PatentsView API Key** (Optional: for innovation activity signals)
*   **Wextractor API Key** (Optional: for Glassdoor review collection)

### 2. Environment Setup
Configure your `.env` file in the root directory:

```bash
# === Snowflake Settings ===
SNOWFLAKE_ACCOUNT="your-org-your-account"
SNOWFLAKE_USER="your-user"
SNOWFLAKE_PASSWORD="your-password"
SNOWFLAKE_DATABASE="PE_ORGAIR"
SNOWFLAKE_SCHEMA="PUBLIC"

# === Infrastructure ===
REDIS_HOST="redis"
NEXT_PUBLIC_API_URL="http://localhost:8000"

# === External Integration (Optional) ===
AWS_ACCESS_KEY_ID="your-key"
AWS_SECRET_ACCESS_KEY="your-secret"
S3_BUCKET="pe-intelligence-parsed"
PATENTSVIEW_API_KEY="your-patentsview-key"
WEXTRACTOR_API_KEY="your-wextractor-key"
```

### 3. Build and Launch
```bash
docker compose --env-file .env -f docker/docker-compose.yml up --build
```
*   **Frontend Hub**: `http://localhost:3000`
*   **API Backbone**: `http://localhost:8000`
*   **Airflow UI**: `http://localhost:8080`
*   **Interactive Tutorial**: `http://localhost:3000/tutorial`

### 4. Stopping and Cleanup

**Stop containers and remove images (Recommended):**
```bash
# Stops containers and removes images to free disk space
docker compose --env-file .env -f docker/docker-compose.yml down --rmi all
```
> **Note:** This preserves your data in `./data/` and `./logs/` directories.

**Complete cleanup (includes volumes):**
```bash
# ⚠️ WARNING: This removes Redis data, Airflow metadata, and all volumes
docker compose --env-file .env -f docker/docker-compose.yml down --rmi all --volumes
```

**Periodic maintenance (recommended weekly):**
```bash
# Clean up unused Docker resources
docker system prune -a -f
docker builder prune -f
```

**Check disk usage:**
```bash
# View Docker disk usage
docker system df

# Check data folder size
du -sh data/ logs/
```

---

## 🔄 Airflow Pipeline Orchestration

The platform uses **Apache Airflow 2.x** with the **TaskFlow API** and **Dynamic Task Mapping** to orchestrate all data collection and scoring pipelines. Airflow runs as part of the Docker Compose stack alongside the API and frontend.

### DAG Overview

| DAG ID | Schedule | Description |
| :--- | :--- | :--- |
| `integration_pipeline` | `@daily` | **Core scoring pipeline** — fetches active tickers, then for each company runs parallel analysis tasks (SEC rubric, Board composition, Talent signals, Culture/Glassdoor) and computes the final OrgAIR score. |
| `sec_filing_ingestion` | `@daily` | **SEC ingestion** — downloads latest 10-K/10-Q filings per ticker from EDGAR, parses and chunks documents, stores in S3 + Snowflake. |
| `sec_backfill` | Manual | **SEC backfill** — manually triggered to backfill historical filings for specified tickers with configurable filing types and limits. |
| `sec_quality_monitor` | `@weekly` | **Data quality audit** — validates Snowflake document/chunk counts, checks S3 consistency, and flags zero-chunk documents (parsing failures). |

### Integration Pipeline Workflow
```
fetch_tickers ──► [Per Company (Dynamic Map)] ──►
                   ├── init_assessment
                   ├── analyze_sec       ─┐
                   ├── analyze_board      ├──► finalize_score
                   ├── analyze_talent     │
                   └── analyze_culture   ─┘
```

Each analysis stage runs in **parallel** within a mapped `task_group`. The `finalize_score` task uses `TriggerRule.ALL_DONE` to gracefully handle partial failures and still compute a score from available dimensions.

### SEC Ingestion Workflow
```
get_tickers ──► download_filings (mapped) ──► discover_filings ──► process_filing (mapped) ──► save_to_snowflake (mapped) ──► cleanup
```

Filings are downloaded, parsed into structured chunks, and persisted to Snowflake. Heavy XCom payloads are written to a shared volume instead of the Airflow metadata DB for efficiency.

---

## 🏢 Glassdoor Culture Scoring

The platform incorporates **Glassdoor employee reviews** as a cultural signal dimension for AI-readiness assessment. Reviews are collected via the **Wextractor API**, scored using a **keyword-based rubric**, and aggregated with **recency and employment-status weighting**.

### Review Collection
*   Reviews are fetched from Glassdoor for target companies (e.g., NVDA, JPM, WMT, GE, DG) using the Wextractor API.
*   Raw review JSON is **cached in S3** to avoid redundant API calls during re-runs.
*   Parsed review objects include: rating, title, pros/cons text, review date, and employment status.

### Rubric-Based Scoring
The `RubricScorer` evaluates reviews across **three culture dimensions**, each scored 1–5:

| Dimension | What It Measures | Example Positive Keywords | Example Negative Keywords |
| :--- | :--- | :--- | :--- |
| **Innovation** | Creativity & forward-thinking culture | *"cutting-edge"*, *"encourages new ideas"*, *"creative freedom"* | *"resistant to change"*, *"outdated tools"*, *"bureaucratic"* |
| **Leadership** | Quality of management vision & support | *"empowering leadership"*, *"clear vision"*, *"mentorship"* | *"micromanagement"*, *"poor communication"*, *"no direction"* |
| **Adaptability** | Organizational agility & responsiveness | *"fast-paced"*, *"embraces change"*, *"agile processes"* | *"slow decision-making"*, *"rigid structure"*, *"stagnant"* |

### Weighted Aggregation
Scores are **not simple averages** — each review is weighted by two factors:
1.  **Recency Weight**: More recent reviews are weighted higher to reflect current company culture.
2.  **Employment Status**: Reviews from current employees carry different weight than former employees.

The final per-dimension score is computed as a **weighted average**, and keyword evidence is extracted and stored alongside scores for audit transparency.

### Data Storage
*   Scores are persisted to Snowflake using the `schema_culture.sql` schema.
*   The `glassdoor_queries.py` module contains `MERGE INTO` statements to handle upserts and prevent duplication.
*   Evidence keywords and review metadata are stored for downstream explainability in the frontend dashboards.

---

## ⚙️ Data Pipelines & Orchestration Logic

The system utilizes a multi-stage, asynchronous pipeline architecture designed for resilience and rate-limit compliance.

### **Pipeline Execution Flow**
The `IntegrationPipeline` orchestrates collection in a specific order to optimize data dependency:
1.  **Job Market Analysis**: First pass using **JobSpy** to identify AI hiring signals. This data is cached and used to resolve technical domains in step 2.
2.  **Concurrent Collection**:
    *   **Innovation Sweep**: Parallel fetch from **PatentsView API**.
    *   **Digital Presence**: Concurrent scan of `BuiltWith` and direct site signatures using **Playwright**.
    *   **Leadership Signals**: Scanning for C-suite AI focus.
3.  **Culture Analysis**: **Glassdoor reviews** are fetched, scored via the rubric engine, and persisted with weighted aggregation.
4.  **Scoring Finalization**: All dimension signals are fed into the **OrgAIR Scoring Engine** (VR, HR, Synergy, Confidence calculators) to produce the final composite score.

### **Robustness & Anti-Blocking Strategies**
To ensure uninterrupted operation and avoid IP/Rate-limit blocking, we implemented:
*   **Adaptive Rate Limiting**: The `PatentCollector` uses a custom `AsyncRateLimiter` capped at **45 req/min** to align with PatentsView quotas.
*   **Browser Stealth**: Playwright instances utilize `playwright-stealth` and **User-Agent rotation** to bypass basic bot detection on corporate websites.
*   **Interval Spacing**: SEC and Job pipelines include `asyncio.sleep` (200ms to 2s) between requests to avoid burst-detection.
*   **Retry Mechanisms**: All critical external calls are wrapped with **Exponential Backoff** using the `Tenacity` library.

### **Asynchronous Scalability**
*   **Semaphore Throttling**: The system uses `asyncio.Semaphore(5)` to prevent overwhelming Snowflake connection pools or external APIs.
*   **Non-Blocking Parsing**: Heavy CPU tasks (like parsing 50MB SEC text filings) are delegated to a `ThreadPoolExecutor` to keep the main API event loop responsive.

---

## 📐 Key Design Decisions

### **Single Source of Truth (SSOT)**
Consolidated legacy disjointed tables into a unified `companies` schema. This allows the SEC pipeline to dynamically "anchor" discovered CIKs to existing targets, ensuring a single version of the truth for every portfolio company.

### **Singleton Database Pattern**
Implemented a thread-safe **Snowflake Singleton** manager with a persistent session pool. This reduces API latency by avoiding the heavy SSL handshake required for new Snowflake connections on every request.

### **Graceful Degradation**
Integrations like S3 and PatentsView are designed to fail gracefully. If credentials are missing, the system warns the operator via structured logs but continues to serve existing data and other active collectors.

### **Airflow-Native Task Design**
Each pipeline step is wrapped as an Airflow `@task` with `asyncio.run()` bridging, allowing reuse of the existing async codebase. Dynamic Task Mapping (`expand()`) enables per-ticker parallelism without manual DAG construction.

---

## 🧪 Quality & Verification

The platform maintains a robust test suite covering core logic, API integrity, and performance benchmarks.

### Running Tests
Execute the full suite within the containerized environment:
```bash
# Run all tests
docker compose --env-file .env -f docker/docker-compose.yml exec api pytest -v -s
```

### Test Categories
| Module | Focus Area |
| :--- | :--- |
| **API Integrity** (`test_api.py`) | Validates all REST endpoints, status codes, and payload validation. |
| **Business Logic** (`test_flows.py`) | End-to-end verification of the Assessment → Signal → Score lifecycle. |
| **Concurrency** (`test_concurrency.py`) | Stress tests the system's ability to handle parallel scraping tasks and SEM throttling. |
| **Performance** (`test_performance_cache.py`) | Measures Redis hit rates and latency improvements for cached metrics. |
| **External Systems** (`test_sec_downloader.py`) | Mocks SEC/PatentsView interactions to ensure resilient parsing logic. |
| **Schema Integrity** (`test_models.py`) | Deep validation of Pydantic V2 models and data transformation rules. |
| **Scoring Properties** (`test_scoring_properties.py`) | Property-based tests for the scoring engine calculators (VR, HR, Synergy, Confidence). |

### Continuous Validation
The test suite is designed to be run as part of a CI/CD pipeline, ensuring that changes to the `IntegrationPipeline` do not regress scoring accuracy or rate-limit compliance.

---

## ⚠️ Known Limitations

1.  **Snowflake Constraints**: Unique constraints are metadata-only in Snowflake; duplication is prevented via `MERGE INTO` logic in our DAO layer.
2.  **BuiltWith Rendering**: Certain high-security sites may occasionally block the Playwright scan; the system falls back to job description keyword analysis in these scenarios.
3.  **Glassdoor API Quotas**: The Wextractor API has rate limits; reviews are cached in S3 to minimize redundant calls during pipeline re-runs.

---

## 👥 Team & Contributions

| Member | Contributions |
| :--- | :--- |
| **Aakash** | Base API (Models, Routers, Redis Caching), Signals Pipeline, Frontend (Tutorial, Playground) |
| **Rahul** | Base API (Models, Router, Schemas, AWS), SEC EDGAR Pipeline and Optimization, Frontend (Dashboards) |
| **Abhinav** | Base API (Models, Routers, Docker, Snowflake), SEC EDGAR Pipeline and Optimization, Documentation, Frontend (Playground) |