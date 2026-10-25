"""Application entry point. Payment behavior will be added milestone by milestone."""

from fastapi import FastAPI

app = FastAPI(
    title="Payment Reliability Lab",
    version="0.1.0",
    description="An educational simulator using synthetic payment data.",
)


@app.get("/health")
def health() -> dict[str, str]:
    """A small startup check; it is not an uptime or database check."""
    return {"status": "ok", "mode": "scaffold"}
