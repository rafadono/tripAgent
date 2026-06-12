# TripAgent API Reference Guide (Operations & Authentication)

This guide documents the administrative, operations monitoring (`/ops`), and user-quota/monetization (`/auth`) APIs of TripAgent. These routes run alongside the core planning route (`/plan`) and search endpoints.

---

## 1. Authentication & Monetization APIs (`/auth`)

These endpoints manage user sessions, quota limit validations, and developer-oriented monetization testing.

### `POST /auth/login`
- **Description**: Authenticates a user and issues a session token. Active only if `auth_enabled` is set to `true` in configuration.
- **Request Body**:
  ```json
  {
    "username": "string",
    "password": "string"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "access_token": "string",
    "token_type": "bearer",
    "username": "string"
  }
  ```

### `GET /auth/me`
- **Description**: Retrieves detailed information about the logged-in user's subscription tier, billing status, and daily planning quota.
- **Headers**: `Authorization: Bearer <token>`
- **Response (200 OK)**:
  ```json
  {
    "username": "string",
    "plan_tier": "free | pro",
    "subscription_status": "active | inactive",
    "subscription_renews_at": 1720000000,
    "daily_plan_quota": 5,
    "daily_plan_used": 1
  }
  ```

### `POST /auth/subscribe/dev`
- **Description**: Admin-only utility. Upgrades a user to the `pro` tier for testing billing features and records a simulated subscription fee.
- **Headers**: Requires admin token header.
- **Request Body**:
  ```json
  {
    "username": "string",
    "months": 1
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "ok": true,
    "username": "string",
    "plan_tier": "pro",
    "renews_at": 1720000000
  }
  ```

### `POST /auth/unsubscribe/dev`
- **Description**: Admin-only utility. Downgrades a user back to the `free` tier.
- **Headers**: Requires admin token header.
- **Request Body**:
  ```json
  {
    "username": "string"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "ok": true,
    "username": "string",
    "plan_tier": "free"
  }
  ```

### `GET /auth/monetization/me`
- **Description**: Combines the logged-in user's plan tier with the aggregate system monetization statistics for the last 30 days.
- **Headers**: `Authorization: Bearer <token>`
- **Response (200 OK)**: Detailed aggregate monetization statistics plus user scope info.

---

## 2. Operations & Control APIs (`/ops`)

These endpoints provide administrative controls, financial simulation, and cost forecasting tools. Most routes require a valid admin token.

### `GET /ops/config`
- **Description**: Returns a snapshot of the current server runtime configuration, fallback states, database settings, and specific endpoint rate limits.
- **Headers**: Requires admin token header.
- **Response (200 OK)**:
  ```json
  {
    "costly_endpoints_enabled": true,
    "plan_endpoint_enabled": true,
    "fallback_mode_enabled": false,
    "fallback_message": "string",
    "cache_backend": "redis",
    "rate_limits": {
      "plan": 10,
      "search_places": 100,
      "nearest_parking": 50
    }
  }
  ```

### `GET /ops/metrics`
- **Description**: Retrieves cost metrics detailing total upstream API charges incurred by the system (Google Places and Routes requests).
- **Headers**: Requires admin token.

### `POST /ops/quality-check`
- **Description**: Runs a full itinerary plan simulation against a payload and compiles warnings (e.g. redundant places, extreme wait durations).
- **Headers**: Requires admin token.
- **Request Body**: `PlanRequest` schema.

### `GET /ops/monetization-report`
- **Description**: Retrieves system revenue generated from ad views and active subscriptions.
- **Headers**: Requires admin token.
- **Parameters**: `days` (default `30`).

### `GET /ops/finance/cashflow`
- **Description**: Computes overall net cash flow (monetization inflow minus Google API and custom cloud infrastructure outflows).
- **Headers**: Requires admin token.
- **Parameters**: `month_ym` (format: `YYYY-MM`).

### `POST /ops/finance/infra-cost`
- **Description**: Upserts database entries tracking custom server or cloud operational expenses for a month.
- **Headers**: Requires admin token.
- **Request Body**:
  ```json
  {
    "month_ym": "2026-06",
    "amount": 45.50,
    "notes": "FastAPI hosting on GCP"
  }
  ```

### `POST /ops/finance/reconcile`
- **Description**: Computes monthly profit margins and dynamically updates system price parameters when bills exceed limits.
- **Headers**: Requires admin token.
- **Request Body**:
  ```json
  {
    "month_ym": "2026-06",
    "apply_price": false
  }
  ```

### `GET /ops/finance/feasibility`
- **Description**: Analyzes operational costs against subscription rates to determine system viability margins and break-even user ratios.
- **Headers**: Requires admin token.

### `POST /ops/finance/report`
- **Description**: Triggers a reconciliation and outputs a formatted Markdown/HTML report for the specified month.
- **Headers**: Requires admin token.
- **Request Body**: Same as reconciliation request.

### `POST /ops/finance/report/annual`
- **Description**: Triggers reconciliation and outputs a calendar or fiscal yearly report.
- **Headers**: Requires admin token.
- **Request Body**:
  ```json
  {
    "year": 2026,
    "scope": "calendar"
  }
  ```

### `POST /ops/cost-guard`
- **Description**: Allows administrators to dynamically shut down costly planning endpoints or entire services during cost surges.
- **Headers**: Requires admin token.
- **Request Body**:
  ```json
  {
    "costly_endpoints_enabled": true,
    "plan_endpoint_enabled": false
  }
  ```

### `GET /ops/budget-alerts`
- **Description**: Checks current monthly expenditure against set warnings and soft/hard limits.
- **Headers**: Requires admin token.

### `POST /ops/cost-forecast` (also `/ops/cost-simulator`)
- **Description**: Performs a simulation estimating the future monthly Google API bill given an expected daily active user volume.
- **Headers**: Requires admin token.
- **Request Body**:
  ```json
  {
    "baseline_daily_requests": 1000,
    "horizon_days": 30
  }
  ```

### `POST /ops/workload-replay`
- **Description**: Replays real request workloads from database records over the past hours to run dry-run simulations.
- **Headers**: Requires admin token.
- **Request Body**:
  ```json
  {
    "since_hours": 24,
    "multiplier": 1.5
  }
  ```

### `GET /ops/cache-efficiency`
- **Description**: Provides a breakdown of Redis or memory cache hits, misses, and the subsequent money saved.
- **Headers**: Requires admin token.

### `POST /ops/ab/assign`
- **Description**: Assigns a variant group to a user session based on experiment variables (e.g. comfort, speed, cost optimization variants).
- **Request Body**:
  ```json
  {
    "experiment": "objective_default",
    "session_id": "optional_session_uuid",
    "variants": ["time", "money", "comfort"]
  }
  ```

### `POST /ops/ab/track`
- **Description**: Tracks user conversions and metrics for A/B tests.
- **Request Body**:
  ```json
  {
    "experiment": "objective_default",
    "session_id": "optional_session_uuid",
    "variant": "comfort",
    "event_type": "conversion",
    "value": 1.0
  }
  ```

### `GET /ops/ab/report`
- **Description**: Compiles variant distributions and conversion counts for an active experiment.
- **Headers**: Requires admin token.
- **Parameters**: `experiment`, `since_days`.
