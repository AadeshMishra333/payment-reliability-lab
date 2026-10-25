# Payment Reliability Lab

An educational full-stack project about what happens when a payment request is retried, a provider event arrives twice, or settlement records disagree. The future application uses **synthetic payment data only**. It does not process money, collect card details, or connect to Visa systems.

**Current status: setup scaffold.** The app exposes only `GET /health`. Payment creation, persistence, idempotency, events, reconciliation, frontend and deployment are planned milestones. The repository should never be described as a completed payment system until those parts exist and have been checked.

## Why build this?

The supplied Visa Software Engineering Intern JD emphasizes the full development cycle, testing, reliability, UI, secure development and distributed-systems fundamentals. This project will turn those broad ideas into a traceable user flow and reproducible failure cases. The full [build sequence](docs/ROADMAP.md) defines what to make and when each claim becomes true.

## Repository layout

```text
payment-reliability-lab/
├── app/
│   ├── __init__.py
│   └── main.py          # FastAPI entry point and setup health check
├── tests/
│   └── test_health.py   # Startup smoke check
├── docs/
│   ├── ROADMAP.md       # Stage-by-stage build, learning and verification
│   ├── DECISIONS.md     # Why we chose this scope and stack
│   └── AI_ASSISTANCE.md # AI-generated work versus demonstrated understanding
├── .gitignore
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

Future directories, such as `app/db/`, `app/payments/`, `app/events/`, `app/reconciliation/`, `frontend/` and `scripts/`, will be added when their first real component exists. Empty architecture folders do not show implemented work.

## Run on Windows PowerShell

From this repository folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/health` and `http://127.0.0.1:8000/docs`. If your Python launcher is not installed, substitute `python -m venv .venv` for the first command. The test and run commands should work with Python 3.11+; they have been checked in the workspace with Python 3.12. Stop the server with Ctrl+C.

## The first build milestone

Make one synthetic payment through an API request and read it back from SQLite. Before coding, agree on the request fields and predict what should happen if the same request is submitted twice. Milestone 1 intentionally handles create/read; the idempotency guarantee comes in milestone 2. A passing startup check says only that the current scaffold boots.

## Collaboration and resume evidence

We will work through one milestone at a time: predict a behavior, implement a thin slice, run a success and failure check, trace the data path, then make and explain a small learner-owned change. Claude Opus can draft frontend screens or review a focused code change; its output will be tested and inspected before it is accepted. The [AI assistance log](docs/AI_ASSISTANCE.md) keeps contribution boundaries explicit.

No project-specific resume bullet is ready from this scaffold. A resume bullet will describe only features that run, have meaningful checks and can be explained by Aadesh. Public source alone is not deployment or proof of personal understanding.
