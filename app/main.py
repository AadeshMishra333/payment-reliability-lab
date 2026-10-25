"""Payment Reliability Lab HTTP API. All records are synthetic."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated
import secrets
import uuid

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.models import PaymentInput
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
    def create_payment(data: PaymentInput, session: Session):
        with store.connect(write=True) as conn:
            if conn.execute("SELECT COUNT(*) FROM payments WHERE session=?", (session,)).fetchone()[0] >= 100:
                raise HTTPException(409, "This demo session is limited to 100 payments.")
            payment_id = "pay_" + uuid.uuid4().hex[:16]
            conn.execute(
                "INSERT INTO payments (id,session,request_key,amount_minor,currency,merchant_reference,status,created_at) VALUES (?,?,?,?,?,?,?,?)",
                (payment_id, session, None, data.amount_minor, data.currency, data.merchant_reference, "pending", datetime.now(timezone.utc).isoformat()),
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
        if row is None:
            raise HTTPException(404, "Payment not found in this demo session.")
        return {"payment": payment_view(row)}

    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(ROOT / "static" / "index.html")

    return app


app = create_app()
