from fastapi.testclient import TestClient
import pytest

from app.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "payments.sqlite3")) as api:
        api.headers["X-Demo-Session"] = "a" * 32
        yield api


def payload(amount=50000, reference="ORDER-001"):
    return {"amount_minor": amount, "currency": "INR", "merchant_reference": reference}


def test_create_read_and_restart(tmp_path):
    database = tmp_path / "durable.sqlite3"
    with TestClient(create_app(database)) as first:
        first.headers["X-Demo-Session"] = "a" * 32
        created = first.post("/api/payments", json=payload())
        assert created.status_code == 201
        pid = created.json()["payment"]["id"]
        assert created.json()["payment"]["status"] == "pending"
    with TestClient(create_app(database)) as restarted:
        restarted.headers["X-Demo-Session"] = "a" * 32
        assert restarted.get(f"/api/payments/{pid}").json()["payment"]["amount_minor"] == 50000


@pytest.mark.parametrize("amount", [0, -1, 1.5, True, "50000", 10_000_001])
def test_invalid_amount_creates_no_row(client, amount):
    result = client.post("/api/payments", json=payload(amount))
    assert result.status_code == 422
    assert client.get("/api/payments").json()["payments"] == []


def test_blank_reference_and_unknown_field_rejected(client):
    assert client.post("/api/payments", json=payload(reference="  ")).status_code == 422
    assert client.post("/api/payments", json={**payload(), "amunt_minor": 1}).status_code == 422


def test_session_isolation(client):
    pid = client.post("/api/payments", json=payload()).json()["payment"]["id"]
    client.headers["X-Demo-Session"] = "b" * 32
    assert client.get("/api/payments").json()["payments"] == []
    assert client.get(f"/api/payments/{pid}").status_code == 404


def test_first_slice_has_no_retry_guarantee_yet(client):
    first = client.post("/api/payments", json=payload()).json()["payment"]["id"]
    second = client.post("/api/payments", json=payload()).json()["payment"]["id"]
    assert first != second
    assert len(client.get("/api/payments").json()["payments"]) == 2


def test_index_served(client):
    result = client.get("/")
    assert result.status_code == 200
    assert "Create a synthetic payment" in result.text
