# ARHA Verification and Quality Assurance Audit

Audit time: 2026-06-13 14:58:27 +05:30  
Workspace: `C:\Users\KOKKANTI ARUN KUMAR\Downloads\ARHA-main\ARHA-main`  
Verdict: **FAIL - not deployable or testable end to end**

## Executive Result

**Overall verified QA score: 27/100**

This score is the arithmetic mean of the seven requested category scores below. A blocked
production-critical category receives zero because ARHA cannot demonstrate that capability.
Synthetic accuracy values are based only on the three explicitly controlled resume fixtures
described in this report.

| Category | Score | Result |
|---|---:|---|
| Security | 25/100 | FAIL |
| Performance | 0/100 | FAIL |
| Resume Accuracy | 79/100 | FAIL |
| Job Matching Accuracy | 67/100 | FAIL |
| Company Analysis Accuracy | 0/100 | FAIL |
| API Reliability | 21/100 | FAIL |
| User Experience | 0/100 | FAIL |

## Test Evidence

| Check | Observed result |
|---|---|
| Python compilation | FAIL: `IndentationError` at `backend/app/config.py:30` |
| Backend import | FAIL: `import app.main` stops at the same syntax error |
| Backend pytest | FAIL during collection; zero tests executed |
| Frontend install | PASS: 24 packages installed |
| Frontend dependency audit | PASS: zero npm vulnerabilities reported |
| Frontend build | FAIL: 10 TypeScript/JSX parser errors |
| Python dependency consistency | PASS: `pip check` reported no broken requirements |
| CI lint command | FAIL: Ruff is not installed by `requirements.txt` |
| Production server command | FAIL by inspection: Docker invokes Gunicorn, which is not installed |
| Public source reachability | PASS: Jobicy, Remotive, and Arbeitnow returned HTTP 200 |
| ARHA source adapters | PARTIAL: Jobicy 0, Remotive 20, Arbeitnow 0 in the observed run |
| Database connection/integrity | NOT EXECUTABLE: no `DATABASE_URL`, app cannot import |
| 100/500/1000-user load tests | NOT EXECUTABLE: no runnable backend or frontend |
| UI screenshots/accessibility run | NOT EXECUTABLE: frontend does not compile |
| Full E2E workflow | NOT EXECUTABLE: both application tiers are broken |

## Phase 1 - System Health

| Component | Status | Evidence | Root cause | Recommended fix |
|---|---|---|---|---|
| Frontend | Broken | `npm run build` reports JSX errors at lines 253, 260, 288, 294, 345 | Corrupted JSX and duplicated markup in `main.tsx` | Repair JSX, then add component and browser tests |
| Backend | Broken | Python compile and import fail at `config.py:30` | Invalid declaration `: str = "gpt-4o"` | Restore `openai_model: str = "gpt-4o"` and validate all settings |
| Database | Broken | No DB URL; startup cannot run | Missing configuration plus two incompatible DB layers/schemas | Choose one schema layer, add real Alembic migrations, run DB integration tests |
| Authentication | Broken | App cannot import; routes cannot execute | Startup failure; default production secrets; no password policy | Fail closed on weak secrets, validate password strength, test JWT/RBAC against a DB |
| Storage | Broken | `crypto.py` imports undefined `PASSPHRASE` and `SALT_PATH` | Crypto module targets an older local-file design | Use current settings and a stable externally managed key/salt strategy |
| Background jobs | Broken | `render.yaml` defines no cron worker | Worker code exists but is not deployed or monitored | Add a scheduled worker service, retries, metrics, and dead-letter handling |
| Caching | Broken | Redis settings and packages exist, but no cache client/use exists | Unimplemented integration | Implement only if required; otherwise remove misleading config/dependencies |
| WebSockets | Broken | No WebSocket route or implementation found | Feature absent | Implement and test, or remove it from supported-component claims |
| Notifications | Broken | DB helpers exist, but no routes, worker, SendGrid, or Telegram calls exist | Partial schema-only implementation | Add delivery service, retry/idempotency logic, endpoints, and tests |

## Phase 2 - API Validation

No `.env` file or relevant process environment values were present.

| API | Status | Last test | Response time | Errors / evidence | Fix required |
|---|---|---|---:|---|---|
| OpenAI | Broken | 2026-06-13 14:58 IST | N/A | `OPENAI_API_KEY` missing; backend cannot import | Provide key and add startup validation |
| Tavily | Broken | 2026-06-13 14:58 IST | N/A | `TAVILY_API_KEY` missing | Provide key and test authenticated search |
| Serper | Broken | 2026-06-13 14:58 IST | N/A | Key missing and integration unused | Provide key only if integration is implemented |
| Upstash Redis | Broken | 2026-06-13 14:58 IST | N/A | URL/token missing and integration unused | Configure and implement, or remove |
| SendGrid | Broken | 2026-06-13 14:58 IST | N/A | Key/from address missing and no send path exists | Configure and implement delivery |
| Telegram | Broken | 2026-06-13 14:58 IST | N/A | Token missing and no bot call exists | Configure and implement delivery |
| PostgreSQL/Supabase | Broken | 2026-06-13 14:58 IST | N/A | `DATABASE_URL` missing | Provide a valid PostgreSQL URL |
| Jobicy public API | Partially Working | 2026-06-13 | 15,522.6 ms direct | Direct HTTP 200/5 jobs; ARHA adapter later returned 0 | Log errors and tune timeout/retries |
| Remotive public API | Working externally | 2026-06-13 | 997.7 ms direct | HTTP 200/27 jobs; ARHA adapter returned 20 | Add contract tests and pagination |
| Arbeitnow public API | Partially Working | 2026-06-13 | 1,223.9 ms direct | HTTP 200/100 jobs; ARHA filter returned 0 | Review filtering and expose diagnostics |
| Google Jobs | Broken | 2026-06-13 | N/A | No adapter found | Implement or remove from supported-source claims |
| Career pages | Broken | 2026-06-13 | N/A | No crawler/adapter found | Implement source-specific adapters |
| Crunchbase | Not configured | 2026-06-13 | N/A | No key or integration found | No action unless intended |
| Resend | Not configured | 2026-06-13 | N/A | SendGrid is configured instead | No action unless intended |

Authentication, expiry, unauthorized-response, and rate-limit behavior for keyed APIs could not
be tested without credentials. No key was classified as invalid or expired because no key existed.

### Missing Keys

```text
MISSING_API_KEY:
OPENAI

MISSING_API_KEY:
TAVILY

MISSING_API_KEY:
SERPER

MISSING_API_KEY:
UPSTASH_REDIS_URL

MISSING_API_KEY:
UPSTASH_REDIS_TOKEN

MISSING_API_KEY:
SENDGRID

MISSING_API_KEY:
TELEGRAM
```

```text
ACTION REQUIRED:
Please provide a new OPENAI key.

ACTION REQUIRED:
Please provide a new TAVILY key.

ACTION REQUIRED:
Please provide a new SERPER key if Serper is intended to be used.

ACTION REQUIRED:
Please provide new UPSTASH REDIS credentials if caching is intended to be used.

ACTION REQUIRED:
Please provide a new SENDGRID key if email notifications are intended to be used.

ACTION REQUIRED:
Please provide a new TELEGRAM bot token if Telegram notifications are intended to be used.

ACTION REQUIRED:
Please provide a valid PostgreSQL DATABASE_URL.
```

## Phase 3 - Resume Analysis

Three controlled plaintext fixtures were evaluated against explicit skill ground truth.

| Resume | Expected skills | Observed issues | Precision | Recall |
|---|---|---|---:|---:|
| A: Software Engineer | Python, FastAPI, PostgreSQL, SQL, Docker, REST API | None in this short fixture | 100.0% | 100.0% |
| B: Frontend Developer | React, TypeScript, JavaScript, Next.js, HTML, CSS | Hallucinated Java and machine learning; missed HTML/CSS | 66.7% | 66.7% |
| C: Data Analyst | Python, SQL, pandas, NumPy, data analysis, Tableau, Excel | Hallucinated AWS and TypeScript; missed Tableau/Excel | 71.4% | 71.4% |
| Micro total | 19 expected skills | 4 hallucinated, 4 missed | **78.9%** | **78.9%** |

Verified false-positive reproductions:

- `JavaScript` produces `java` and `javascript`.
- `HTML CSS` produces `machine learning` because `ml` is matched as a substring.
- `Built dashboards` produces `aws`.
- `Built projects` produces `typescript` because `ts` is matched as a substring.
- `I go to work` produces the Go programming language.

ATS scoring was deterministic across repeated calls, but calibration failed the practical
expectation: the strong backend fixture scored only 24 ATS, largely because short synthetic text is
penalized and section quality is approximated by global keyword counts. Education, projects, and
experience are not structurally extracted by the deterministic endpoint. The LLM agent claims those
features, but could not be invoked without OpenAI and the application route does not call it.

## Phase 4 - Job Matching

The deterministic scorer was tested over three resumes and three role descriptions.

| Resume | Relevant role | Relevant-role score | Expected | Result |
|---|---|---:|---|---|
| Software Engineer | Backend | 50 | High | False negative |
| Frontend Developer | Frontend | 52 | High | False negative |
| Data Analyst | Data Scientist | 23 | Higher than unrelated roles | Ranked first, but absolute score too low |

- Classification accuracy on 9 controlled relevant/unrelated pairs: **66.7%**.
- Top-1 ranking accuracy on the 3 controlled resumes: **100%**.
- All six intentionally unrelated pairs were correctly low.
- All three relevant pairs failed to reach the scorer's own `Moderate Match` threshold of 55.
- False-positive skill extraction contaminates both required-skill and resume-skill sets.
- The API route is broken independently: it calls `_match_agent.match`, but the agent implements
  `score`, not `match`.

## Phase 5 - Company Intelligence

Status: **Broken / not measurable**

- OpenAI and Tavily keys are missing.
- The router passes `domain`, `include_culture`, and `include_financials`, but the agent method accepts
  only `company_name` and `job_title`; this would raise `TypeError`.
- The quick-search route calls `_company_agent.search`, which does not exist.
- Tavily exceptions are silently discarded.
- If every search fails, the code still asks OpenAI to score a company using the text
  `No search results found.` This permits unsupported trust scores and hallucinated facts.
- No provenance validation confirms that model-returned `data_sources` match fetched URLs.

Google, Microsoft, Amazon, and an unknown startup could not be scored honestly. Trust-score
accuracy, evidence quality, and confidence are therefore **not established**.

## Phase 6 - Job Sources

| Source | External API | ARHA adapter | Jobs observed | Pagination | Error handling |
|---|---|---|---:|---|---|
| Jobicy | HTTP 200 | Partial | 5 direct / 0 adapter | Fixed count only | Exceptions swallowed |
| Remotive | HTTP 200 | Working in adapter test | 27 direct / 20 adapter | No real page traversal | Exceptions swallowed |
| Arbeitnow | HTTP 200 | Partial | 100 direct / 0 after filter | Hardcoded page 1 | Exceptions swallowed |
| Google Jobs | Absent | Broken | 0 | Absent | Absent |
| Career pages | Absent | Broken | 0 | Absent | Absent |

Deduplication passed a three-record synthetic test, reducing records sharing URL or normalized
title/company to one. Freshness ordering passed a synthetic new/unknown/old ordering test. The
computed freshness value is not written back to returned jobs, and pagination inputs accepted by
the route cannot be honored because `JobSearchAgent.search` does not exist.

## Phase 7 - Application Workflow

Status: **Broken**

- `/jobs/apply` creates an internal pending record; it does not submit to an employer.
- Admin approval is RBAC-protected in source.
- No employer submission endpoint exists, so the claimed complete application workflow is absent.
- There is no resume-optimization approval prerequisite in the current `/jobs/apply` flow.
- The old approval-bypass test targets removed SQLite endpoints and cannot execute.
- Direct endpoint bypass testing was blocked by backend import failure.
- Public job search, matching, keyword analysis, registration, and logout routes have no rate limit.

## Phase 8 - Security Findings

| Severity | CVSS | Finding | Proof | Fix |
|---|---:|---|---|---|
| Critical | 9.1 | Default JWT and encryption secrets allowed | `config.py:15,20` | Reject defaults at startup; use managed secrets and rotation |
| High | 8.2 | No rate limiting on costly/public APIs | SlowAPI is installed but unused | Apply per-IP/user limits and upstream backoff |
| High | 8.1 | Unbounded upload memory consumption | `await file.read()` with no size cap at `resume.py:62` | Stream, cap size, and reject oversized files |
| High | 7.5 | MIME-only file validation | Upload trusts client `content_type` | Validate magic bytes, parser safety, page count, decompression limits |
| High | 7.5 | Company scores can be generated without evidence | Search exceptions swallowed; LLM still runs | Fail closed when evidence is absent |
| Medium | 6.5 | Weak-password registration | `password: str` has no length/complexity check | Add policy and breached-password controls |
| Medium | 6.5 | Logout does not revoke JWT | Endpoint only tells client to discard token | Use short-lived access tokens plus revocation/refresh rotation |
| Medium | 6.3 | Overly broad CORS methods/headers | Wildcards in `main.py:55-56` | Restrict to required methods and headers |
| Medium | 5.9 | Missing browser CSP/HSTS/referrer policy | Vercel headers omit them | Add CSP, HSTS, Referrer-Policy, Permissions-Policy |
| Medium | 5.3 | Detailed validation body echoed | `main.py` returns `str(exc.body)` | Do not reflect submitted bodies in error responses |

Positive controls found: SQL values are parameterized, resume ownership is checked on retrieval,
admin approval uses an RBAC dependency, React normally escapes rendered text, and npm reported no
known dependency vulnerabilities. These controls were source-reviewed, not runtime-validated.

## Phase 9 - Database

Status: **Broken / not executable**

- PostgreSQL is not configured or connected.
- No `alembic.ini` or migration versions directory exists.
- Startup uses ORM `Base.metadata.create_all`, while application helpers use a separate raw-DDL
  schema with incompatible column names and types.
- `main.py` imports `Base` but does not import `models` before `create_all`, so metadata can be empty.
- The raw DB engine required by `app.db` is never initialized by `main.py`, which initializes the
  separate engine in `database.py`.
- Duplicate job prevention differs between schemas and cannot be verified against real data.
- Orphans, corrupt resumes, slow queries, indexes, and migration state could not be queried.

**Database health score: 0/100.**

## Phase 10 - Performance

Status: **FAIL - load test not executable**

The 100, 500, and 1000 concurrent-user tests were not run because no backend process can start and
no database is configured. Reporting latency, CPU, memory, database load, or error rate would be
fabricated. A direct external check found Jobicy took 15.5 seconds, which is close to or beyond the
adapter's 15-second timeout and can cause empty results.

## Phase 11 - Frontend

Status: **Broken**

- TypeScript build fails with malformed JSX.
- The frontend calls obsolete routes such as `/jobs`, `/audit-log`, `/resume/versions`,
  `/jobs/search/local`, and `/approvals`; the current backend exposes different routes.
- The frontend sends no bearer token, while resume/company/application routes require one.
- Upload UI accepts PDF only although the backend claims PDF and DOCX.
- Dark mode exists as the only theme; no theme toggle was found.
- Loading is represented mainly by disabled buttons; route-level and skeleton states are absent.
- Several controls are nonfunctional alerts or non-interactive navigation spans.
- Screenshots, responsive browser checks, keyboard checks, contrast measurements, and automated
  accessibility scans could not run because the application does not compile.

## Phase 12 - End-to-End

| Step | Result |
|---|---|
| 1. Upload resume | FAIL |
| 2. Analyze resume | FAIL |
| 3. Fetch jobs | FAIL through API; public providers reachable directly |
| 4. Analyze companies | FAIL |
| 5. Generate matches | FAIL through API; deterministic function runs in isolation |
| 6. Optimize resume | FAIL |
| 7. Request approval | FAIL |
| 8. Submit application | Not implemented |

## Phase 13 - Observability

Status: **Broken**

- Basic standard-output logging exists.
- No Sentry initialization exists.
- No metrics, traces, request IDs, structured event schema, dashboards, alerts, or uptime checks exist.
- Source adapters suppress exceptions, creating major operational blind spots.
- The `/health` endpoint reports a constant healthy response and does not test database or providers.
- No notification delivery telemetry or background-worker heartbeat exists.

## Root-Cause Summary

1. The repository combines incompatible old SQLite/frontend/tests with a newer PostgreSQL/router
   implementation.
2. Configuration was partially corrupted and lacks fields referenced by runtime code.
3. Router-to-service interfaces were changed without contract tests.
4. CI and Docker commands reference dependencies not installed by the project.
5. External-service failures are swallowed, preventing diagnosis and causing false empty results.
6. No deployable environment configuration or production test data was provided.

## Required Remediation Order

1. Restore syntactic validity and define every referenced setting.
2. Select one backend architecture and remove the incompatible database/schema generation.
3. Align router calls with service method names and signatures.
4. Align the frontend API contract and add authentication state.
5. Replace obsolete tests with contract, DB integration, and approval-bypass tests.
6. Add missing runtime/CI dependencies and a real migration chain.
7. Enforce secure secret validation, upload limits, and rate limits.
8. Add provider diagnostics, retries, and evidence-required company scoring.
9. Configure credentials and a disposable PostgreSQL test database.
10. Only then run browser, E2E, database-integrity, and 100/500/1000-user load tests.

## Final Module Verdicts

| Module | Verdict |
|---|---|
| Frontend | FAIL |
| Backend | FAIL |
| Database | FAIL |
| Authentication | FAIL |
| Storage/encryption | FAIL |
| Resume extraction/analysis | FAIL |
| Job matching | FAIL |
| Company intelligence | FAIL |
| Job-source aggregation | FAIL |
| Application workflow | FAIL |
| Background worker | FAIL |
| Caching | FAIL |
| WebSockets | FAIL |
| Notifications | FAIL |
| Security readiness | FAIL |
| Performance readiness | FAIL |
| Observability | FAIL |
| End-to-end workflow | FAIL |

No API key was verified as invalid or expired. All configured keyed integrations are missing
credentials, and ARHA must not be treated as production-ready until the failed checks are rerun
successfully in a configured environment.
