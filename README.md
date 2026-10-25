# Payment Reliability Lab

An educational full-stack project about what happens when a payment request is retried, a provider event arrives twice, or settlement records disagree. The future application uses **synthetic payment data only**. It does not process money, collect card details, or connect to Visa systems.

**Current status: working local full-stack demo.** The app creates and reads synthetic INR payments in SQLite through the browser. A zero amount is rejected with an on-screen message. A repeated request key with the same payload returns the original payment; changed payloads conflict. The browser can submit [simulated provider events](docs/EVENT_CONTRACT.md) and show [read-only settlement comparisons](docs/RECONCILIATION_CONTRACT.md). Public hosting is not yet active.

## Why build this?

The supplied Visa Software Engineering Intern JD emphasizes the full development cycle, testing, reliability, UI, secure development and distributed-systems fundamentals. This project will turn those broad ideas into a traceable user flow and reproducible failure cases. The full [build sequence](docs/ROADMAP.md) defines what to make and when each claim becomes true.

## Repository layout

```text
payment-reliability-lab/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI routes and session-scoped operations
│   ├── models.py        # Validated payment, event and CSV input
│   ├── reconciliation.py # CSV parsing and exception classification
│   └── storage.py       # SQLite connection and schema
├── tests/
│   ├── test_health.py   # Startup smoke check
│   ├── test_payments.py # Persistence, validation and isolation checks
│   ├── test_events.py   # Duplicate delivery and transition cases
│   └── test_reconciliation.py # CSV and exception cases
├── static/              # Browser form, event timeline and comparison UI
├── docs/
│   ├── ROADMAP.md       # Stage-by-stage build, learning and verification
│   ├── API_CONTRACT.md  # First payment request and zero-amount behavior
│   ├── EVENT_CONTRACT.md # Manual event simulator and state rules
│   ├── RECONCILIATION_CONTRACT.md # CSV comparison and exception meanings
│   ├── DECISIONS.md     # Why we chose this scope and stack
│   └── AI_ASSISTANCE.md # AI-generated work versus demonstrated understanding
├── .github/workflows/ci.yml # Test suite on pushes and pull requests
├── render.yaml           # Free demo hosting configuration; ephemeral SQLite
├── .gitignore
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

Further modules, including asynchronous work, will be added when their first real behavior exists. Empty architecture folders do not show implemented work.

## Run on Windows PowerShell

From this repository folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/` for the browser demo, `http://127.0.0.1:8000/health` for health, and `http://127.0.0.1:8000/docs` for the API. Create a payment, retry with the same key, select it, send a simulated event, fill a settlement CSV and compare. If your Python launcher is not installed, substitute `python -m venv .venv` for the first command. The test and run commands should work with Python 3.11+; they have been checked in the workspace with Python 3.12. Stop the server with Ctrl+C.

GitHub Actions also runs the test on pushes to `main` and pull requests. The workflow checks out the repository with read-only GitHub permissions and does not use deployment credentials.

## Verification and hosting limit

The assistant ran 36 local tests. In the browser, it checked zero-amount validation, create/retry/conflict, a successful event and its duplicate, a matching settlement row and an amount mismatch. Aadesh's own trace and change are pending. A random demo-session token scopes records; it is not a production login.

The included [Render blueprint](render.yaml) prepares a free public web demo, but no Render service or URL exists yet. Render's free web filesystem is ephemeral: SQLite records can disappear after a restart or redeploy. The site and API say *synthetic demo*; do not use real financial data. For durable hosted records, migrate to a hosted database or a paid persistent disk first. See [deployment notes](docs/DEPLOYMENT.md).

## Collaboration and resume evidence

We will work through one milestone at a time: predict a behavior, implement a thin slice, run a success and failure check, trace the data path, then make and explain a small learner-owned change. Claude Opus can draft frontend screens or review a focused code change; its output will be tested and inspected before it is accepted. The [AI assistance log](docs/AI_ASSISTANCE.md) keeps contribution boundaries explicit.

A resume bullet can describe these implemented features after Aadesh can trace and explain them. Public source alone is not deployment or proof of personal understanding. The mature outbox, production-grade access control, PostgreSQL migration and load study in the roadmap are still future work; do not claim them today.
