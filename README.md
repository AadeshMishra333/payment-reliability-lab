# Payment Reliability Lab

An educational full-stack project about what happens when a payment request is retried, a provider event arrives twice, or settlement records disagree. The future application uses **synthetic payment data only**. It does not process money, collect card details, or connect to Visa systems.

**Current status: payment API plus event simulator.** The app creates and reads synthetic INR payments in SQLite through a browser form. A zero amount is rejected with an on-screen message. A repeated request key with the same payload returns the original payment; changed payloads conflict. The API now accepts [simulated provider events](docs/EVENT_CONTRACT.md) and records their state transitions. The browser event controls, reconciliation and deployment are upcoming milestones.

## Why build this?

The supplied Visa Software Engineering Intern JD emphasizes the full development cycle, testing, reliability, UI, secure development and distributed-systems fundamentals. This project will turn those broad ideas into a traceable user flow and reproducible failure cases. The full [build sequence](docs/ROADMAP.md) defines what to make and when each claim becomes true.

## Repository layout

```text
payment-reliability-lab/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI routes and session-scoped create/read
│   ├── models.py        # Validated payment input
│   └── storage.py       # SQLite connection and schema
├── tests/
│   ├── test_health.py   # Startup smoke check
│   └── test_payments.py # Persistence, validation and isolation checks
├── static/              # Minimal accessible browser form
├── docs/
│   ├── ROADMAP.md       # Stage-by-stage build, learning and verification
│   ├── API_CONTRACT.md  # First payment request and zero-amount behavior
│   ├── EVENT_CONTRACT.md # Manual event simulator and state rules
│   ├── DECISIONS.md     # Why we chose this scope and stack
│   └── AI_ASSISTANCE.md # AI-generated work versus demonstrated understanding
├── .github/workflows/ci.yml # Same startup check on pushes and pull requests
├── .gitignore
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

Future modules, such as provider events and reconciliation, will be added when their first real behavior exists. Empty architecture folders do not show implemented work.

## Run on Windows PowerShell

From this repository folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/health` and `http://127.0.0.1:8000/docs`. If your Python launcher is not installed, substitute `python -m venv .venv` for the first command. The test and run commands should work with Python 3.11+; they have been checked in the workspace with Python 3.12. Stop the server with Ctrl+C.

GitHub Actions also runs the test on pushes to `main` and pull requests. The workflow checks out the repository with read-only GitHub permissions and does not use deployment credentials.

## The first build milestone

The create/read, safe-retry and event API milestones now run. The assistant ran 25 local tests; the browser has been checked for create, retry, conflict and zero-amount paths. Event controls are still an API-only step until the UI milestone. Aadesh's own trace and change are pending. A random demo-session token scopes records; it is not a production login.

## Collaboration and resume evidence

We will work through one milestone at a time: predict a behavior, implement a thin slice, run a success and failure check, trace the data path, then make and explain a small learner-owned change. Claude Opus can draft frontend screens or review a focused code change; its output will be tested and inspected before it is accepted. The [AI assistance log](docs/AI_ASSISTANCE.md) keeps contribution boundaries explicit.

No project-specific resume bullet is ready from this scaffold. A resume bullet will describe only features that run, have meaningful checks and can be explained by Aadesh. Public source alone is not deployment or proof of personal understanding.
