"""Payment Reliability Lab HTTP API. All records are synthetic."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated
import secrets
import uuid

from fastapi import FastAPI, Header, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.models import EventInput, PaymentInput
from app.storage import PaymentStore

ROOT = Path(__file__).resolve().parents[1]
Session = Annotated[str, Header(alias="X-Demo-Session", pattern=r"^[a-f0-9]{32}$")]


def payment_view(row) -> dict:
    return {key: row[key] for key in ("id", "amount_minor", "currency", "merchant_reference", "status", "created_at")}


def create_app(database_path: str | Path | None = None) -> FastAPI:
    store = PaymentStore(database_path)
    app = FastAPI(title="Payment Reliability Lab", version="0.1.0", description=__doc__)

    @app.get("/health")
    def health() -> dict[str, str]:
        with store.connect() as conn:
            conn.execute("SELECT 1").fetchone()
        return {"status": "ok", "mode": "synthetic-demo"}

    @app.post("/api/session")
    def new_session():
        return {"token": secrets.token_hex(16)}

    @app.post("/api/payments", status_code=201)
    def create_payment(
        data: PaymentInput,
        session: Session,
        response: Response,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")],
    ):
        with store.connect(write=True) as conn:
            existing = conn.execute(
                "SELECT * FROM payments WHERE session=? AND request_key=?",
                (session, idempotency_key),
            ).fetchone()
            if existing is not None:
                if any(existing[name] != getattr(data, name) for name in ("amount_minor", "currency", "merchant_reference")):
                    raise HTTPException(409, "This request key belongs to a different payment payload.")
                response.status_code = 200
                return {"payment": payment_view(existing), "replayed": True}
            if conn.execute("SELECT COUNT(*) FROM payments WHERE session=?", (session,)).fetchone()[0] >= 100:
                raise HTTPException(409, "This demo session is limited to 100 payments.")
            payment_id = "pay_" + uuid.uuid4().hex[:16]
            conn.execute(
                "INSERT INTO payments (id,session,request_key,amount_minor,currency,merchant_reference,status,created_at) VALUES (?,?,?,?,?,?,?,?)",
                (payment_id, session, idempotency_key, data.amount_minor, data.currency, data.merchant_reference, "pending", datetime.now(timezone.utc).isoformat()),
            )
            row = conn.execute("SELECT * FROM payments WHERE id=?", (payment_id,)).fetchone()
        return {"payment": payment_view(row), "replayed": False}

    @app.get("/api/payments")
    def list_payments(session: Session):
        with store.connect() as conn:
            rows = conn.execute("SELECT * FROM payments WHERE session=? ORDER BY created_at DESC LIMIT 100", (session,)).fetchall()
        return {"payments": [payment_view(row) for row in rows]}

    @app.get("/api/payments/{payment_id}")
    def read_payment(payment_id: str, session: Session):
        with store.connect() as conn:
            row = conn.execute("SELECT * FROM payments WHERE id=? AND session=?", (payment_id, session)).fetchone()
            events = conn.execute("SELECT event_id,status,applied,created_at FROM events WHERE payment_id=? AND session=? ORDER BY id", (payment_id, session)).fetchall()
        if row is None:
            raise HTTPException(404, "Payment not found in this demo session.")
        return {"payment": payment_view(row), "events": [dict(event) for event in events]}

    @app.post("/api/payments/{payment_id}/events")
    def receive_event(payment_id: str, data: EventInput, session: Session):
        """Apply a synthetic status event at most once by event ID."""
        with store.connect(write=True) as conn:
            payment = conn.execute("SELECT * FROM payments WHERE id=? AND session=?", (payment_id, session)).fetchone()
            if payment is None:
                raise HTTPException(404, "Payment not found in this demo session.")
            prior = conn.execute("SELECT * FROM events WHERE event_id=? AND session=?", (data.event_id, session)).fetchone()
            if prior is not None:
                if prior["payment_id"] != payment_id or prior["status"] != data.status:
                    raise HTTPException(409, "Event ID was reused with different content.")
                return {"payment": payment_view(payment), "replayed": True, "applied": False}
            if payment["status"] != "pending" and data.status != payment["status"]:
                raise HTTPException(409, "A terminal payment cannot change state in this simulation.")
            applied = payment["status"] != data.status
            conn.execute("UPDATE payments SET status=? WHERE id=?", (data.status, payment_id))
            conn.execute(
                "INSERT INTO events (session,event_id,payment_id,status,applied,created_at) VALUES (?,?,?,?,?,?)",
                (session, data.event_id, payment_id, data.status, int(applied), datetime.now(timezone.utc).isoformat()),
            )
            updated = conn.execute("SELECT * FROM payments WHERE id=?", (payment_id,)).fetchone()
        return {"payment": payment_view(updated), "replayed": False, "applied": applied}

    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(ROOT / "static" / "index.html")

    return app


app = create_app()
