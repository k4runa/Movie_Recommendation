# 🔧 CineWave — Security & Reliability Fixes (2026-04-19)

This document details all fixes applied as a result of a comprehensive security audit.

---

## 🔴 Critical Fixes

### 1. Removed Hardcoded Database Credentials from `alembic.ini`
**File:** `alembic.ini`
Database credentials were stored in plaintext. Replaced with a non-functional placeholder; the actual URL is loaded from `DATABASE_URL_SYNC` environment variable via `env.py`.

### 2. Closed DoS Vector on Chat Endpoint
**File:** `routers/ai.py`
`ChatRequest.message` was an unconstrained `str` — a client could send a 100MB JSON body and crash the server.
- `message`: `max_length=5000`
- `history`: max 20 messages, each `max_length=5000`

### 3. Removed Internal Error Detail Leak
**File:** `routers/ai.py`
`str(e)` was returned directly to the client — attackers could see internal stack traces. Now returns an opaque error message; details are only logged server-side.

### 4. Removed `unsafe-eval` from Content Security Policy
**File:** `main.py`
The CSP header contained `'unsafe-eval'`, which effectively disabled XSS protection entirely. Now each directive (`script-src`, `style-src`, `img-src`, `connect-src`, `font-src`) is whitelisted individually. Also added `X-XSS-Protection`, `Referrer-Policy`, and `frame-ancestors 'none'`.

### 5. Soft-Deleted Users Could Still Log In
**File:** `services/database.py`
`get_user_by_username()` and `user_exists()` queries did not filter on `is_deleted`. Soft-deleted users had full access to all endpoints. Added `User.is_deleted == False` filter.

---

## 🟠 High Priority Fixes

### 6. Added Password Minimum Length
**File:** `services/schemas.py`
`UserScheme.password` now requires `min_length=8`. Single-character passwords are no longer accepted.

### 7. Username Changes Now Require Password Verification
**File:** `services/database.py`
`update_user_field()` only required the current password for password and email changes. Username changes (which also issue a new JWT!) could be done without verification. Added `"username"` to the password-required fields set.

### 8. Enforced Hard Pagination Limits
**File:** `services/database.py`
`get_all_users()` and `get_watched_movies()` accepted arbitrary `limit` values. A client could request `?limit=1000000` and exhaust server memory. Both now enforce `limit = min(limit, 100)`.

### 9. Added Frontend 401 Response Interceptor
**Files:** `web/src/lib/api.ts`, `web/src/lib/store.ts`
Expired JWT tokens caused silent failures — the UI appeared authenticated while all API calls returned 401. Now the axios interceptor catches 401 responses and dispatches an `auth-expired` event; the Zustand store listens and triggers automatic logout.

### 10. Added `max_length` Constraints to Schema Fields
**Files:** `services/schemas.py`, `routers/users.py`
- `UserScheme.device/os/machine/memory` → `max_length=100`
- `MovieScheme.query` → `max_length=200`
- `UpdateUserRequest.field` → `max_length=50`
- `UpdateUserRequest.current_password` → `max_length=128`

### 11. `tmdb_id` Type Safety
**File:** `services/schemas.py`
Was `str | int` — now `int = Field(0, ge=0, le=999999999)`. String injection is no longer possible.

### 12. Docker Container Hardening
**File:** `docker-compose.yml`
- Added `restart: unless-stopped`
- Added `memory: 512M`, `cpus: 0.5` resource limits
- Added healthcheck (uses the `/health` endpoint)

### 13. Added `/health` Endpoint
**File:** `main.py`
Lightweight `GET /health → {"status": "healthy"}` endpoint for Docker, Render, and load balancer health probes.

---

## 🟡 Medium Priority Fixes

### 14. `max_toasts` Default Mismatch
**File:** `services/database.py`
Python `default=5` but `server_default="3"`. Rows created via ORM got 5; rows created via raw SQL got 3. Both are now aligned to `5`.

---

## 📦 Additional Files

### `.env.example` Updated
Contains all required environment variables as safe placeholders.

### `.gitignore` Updated
- Added `.pytest_cache/`, `.ruff_cache/`, `htmlcov/`, `.coverage`
- Added `AUDIT_REPORT.md` (contains security findings, should not be public)

---

---

## 🔒 Phase 2 Security Hardening (2026-04-19)

### 15. Broken Token Lifecycle Fixed
**Files:** `services/auth.py`, `routers/users.py`
Previously, `get_current_user` only verified cryptographic validity without checking the database. A user could delete their account but continue using their active JWT. The system now enforces `is_deleted == False` on every request. Furthermore, deleting an account or changing credentials now explicitly blacklists the active token to prevent reuse.

### 16. Rate Limiting Enforced (SlowAPI)
**Files:** `main.py`, `routers/auth.py`, `routers/ai.py`, `requirements.txt`
The API was vulnerable to brute-force credential stuffing and AI cost abuse. Implemented `slowapi`:
- `POST /login`: Limited to 5 requests per minute per IP.
- `POST /ai/chat`: Limited to 10 requests per minute per IP.

### 17. Strict AI Timeouts
**File:** `services/ai.py`
External AI SDKs (`genai.Client`, `AsyncGroq`) were allowed to hang indefinitely on network failure, which could lock up FastAPI workers. Wrapped all synchronous and streaming AI calls in `asyncio.wait_for(..., timeout=15.0)` to guarantee worker release.
