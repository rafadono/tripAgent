# TripAgent

An urban route planning assistant and optimizer powered by FastAPI, OR-Tools, and the Google Places & Routes APIs.
This repository features budget control guardrails, Ads & Subscription monetization models, cash flow simulations, and monthly/annual operational reporting.

The codebase (comments, exceptions, docstrings, variable definitions, and server-side logs) is entirely written in English, while the user interface supports seamless real-time switching between English and Spanish via a toggle button.

---

## Technical Stack & Architecture

- **Backend**: FastAPI (Python 3.12+), Pydantic v2, OR-Tools routing solver, HTTPX, SQLite database.
- **Frontend**: Vanilla HTML5, CSS3 variables, and Leaflet maps with client-side dynamic i18n support.
- **Cache & Queue**: Redis.
- **Automation**: GitHub Actions CI workflow.
- **Containerization**: Multi-stage Dockerfile utilizing Astral `uv` for lightning-fast package dependency resolution.

---

## Performance & Optimization Review (Python vs. Rust)

During our performance review, we evaluated whether the route optimization solver should be rewritten in Rust to resolve bottlenecks:
- **Solver Performance**: The routing solver (`solver_ortools.py`) wraps **Google OR-Tools** (`pywrapcp`), which is a compiled C++ constraint solver engine. Formulation and execution of the C++ solver takes **< 5ms** for standard routes.
- **Actual Bottleneck**: The primary performance bottleneck is **network latency** from upstream API requests to the Google Places API (for POI details) and Google Routes API (for distance/duration matrices), which can take **100ms - 1000ms+**.
- **Conclusion**: A Rust rewrite of the mathematical model formulation in python would save less than **1ms** of binding overhead, while introducing heavy compilation complexity (Rust compilers in Docker, binary wheel packaging). The system is already optimized via parallel async requests (`place_details_many`) and Redis/Memory caching to address the real I/O bottleneck.

---

## API Reference Documentation

For details on all administrative operations and user authentication APIs, see:
- [API Reference Guide](file:///c:/Users/RafaelInostroza/Desktop/tripAgent/API_REFERENCE.md)

---

## Quick Start (Docker Compose)

The repository provides a single, consolidated `docker-compose.yml` to run the services.

### Core Application & Redis Cache

Start the core backend API and the Redis database:
```bash
docker compose up -d --build
```

Access links:
- **Web Interface (UI)**: [http://localhost:8000/](http://localhost:8000/)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health check**: [http://localhost:8000/health/ready](http://localhost:8000/health/ready)

### Optional Nginx Monetization Proxy

To serve static landing pages directly via Nginx (useful for Google AdSense compliance and SEO crawling), run:
```bash
# Starts core services along with the Nginx reverse proxy
docker compose up -d nginx-proxy
```
Access the public landing page via Nginx at `http://localhost:8080/`. The reverse proxy configuration in Nginx automatically routes API requests back to the core FastAPI container on port 8000.

---

## Configuration & Environment Variables (`.env`)

Use `.env.example` as a template to create your `.env` file. The minimum required variable to run optimization plans is:
```env
GOOGLE_MAPS_API_KEY="your_google_cloud_api_key"
```

Other optional parameters:
- `TRIPAGENT_DB_PATH`: Path to the SQLite storage file (defaults to `out/tripagent.db`).
- `TRIPAGENT_HEALTH_CHECK_UPSTREAM_ENABLED`: Enable/disable health checks directly probing upstream Google APIs on startup.

---

## Operations & Scheduled Tasks

To execute automated monthly or annual financial reports, run:
```bash
# Automatic end-of-month check and price adjustments
docker exec tripagent python ops/finance_report_job.py --mode auto --apply-price
```
You can configure a cron job or scheduled task on your host machine to run this command periodically.

---

## Running Tests & Quality Checks

### Automated Tests
Run the unit test suite locally or inside the Docker container:
```bash
# Local execution
python -m unittest discover tests

# Docker container execution
docker exec tripagent python -m unittest discover -s tests -p "test_*.py"
```

### CI/CD Automation (GitHub Actions)
The repository is pre-configured with a GitHub Actions workflow located in `.github/workflows/ci.yml`. On every `push` and `pull_request` to the `main` branch, the runner:
1. Provisions a Redis service container.
2. Checks syntax and coding standards using `ruff`.
3. Discovers and runs the full test suite.