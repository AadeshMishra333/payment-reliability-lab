from fastapi.testclient import TestClient
import pytest

from app.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "payments.sqlite3")) as api:
        api.headers["X-Demo-Session"] = "a" * 32
        api.headers["Idempotency-Key"] = "order-001-attempt"
        yield api


def payload(amount=50000, reference="ORDER-001"):
    return {"amount_minor": amount, "currency": "INR", "merchant_reference": reference}


def test_create_read_and_restart(tmp_path):
    database = tmp_path / "durable.sqlite3"
    with TestClient(create_app(database)) as first:
        first.headers["X-Demo-Session"] = "a" * 32
        first.headers["Idempotency-Key"] = "order-001-attempt"
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


def test_same_key_and_payload_replays_one_operation(client):
    first = client.post("/api/payments", json=payload())
    retry = client.post("/api/payments", json=payload())
    assert first.status_code == 201
    assert retry.status_code == 200 and retry.json()["replayed"]
    assert first.json()["payment"]["id"] == retry.json()["payment"]["id"]
    assert len(client.get("/api/payments").json()["payments"]) == 1


def test_same_key_with_changed_payload_conflicts(client):
    original = client.post("/api/payments", json=payload()).json()["payment"]["id"]
    changed = client.post("/api/payments", json=payload(amount=60000))
    assert changed.status_code == 409
    assert client.get(f"/api/payments/{original}").json()["payment"]["amount_minor"] == 50000


def test_parallel_same_key_requests_still_make_one_payment(client):
    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(lambda _: client.post("/api/payments", json=payload()), range(12)))
    assert sum(r.status_code == 201 for r in responses) == 1
    assert all(r.status_code in {200, 201} for r in responses)
    assert len({r.json()["payment"]["id"] for r in responses}) == 1


def test_parallel_conflicting_payloads_do_not_overwrite(client):
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda amount: client.post("/api/payments", json=payload(amount)), [50000, 60000]))
    assert sorted(r.status_code for r in responses) == [201, 409]
    assert len(client.get("/api/payments").json()["payments"]) == 1


def test_missing_key_rejected(client):
    del client.headers["Idempotency-Key"]
    assert client.post("/api/payments", json=payload()).status_code == 422


def test_index_served(client):
    result = client.get("/")
    assert result.status_code == 200
    assert "Create a synthetic payment" in result.text
from concurrent.futures import ThreadPoolExecutor
