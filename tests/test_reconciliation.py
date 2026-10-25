from fastapi.testclient import TestClient
import pytest

from app.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "reconcile.sqlite3")) as api:
        api.headers["X-Demo-Session"] = "a" * 32
        yield api


def payment(client, key):
    response = client.post("/api/payments", headers={"Idempotency-Key": key}, json={"amount_minor": 50000, "currency": "INR", "merchant_reference": key})
    assert response.status_code == 201
    return response.json()["payment"]["id"]


def mark_succeeded(client, pid, eid):
    result = client.post(f"/api/payments/{pid}/events", json={"event_id": eid, "status": "succeeded"})
    assert result.status_code == 200


def reconcile(client, csv_text):
    return client.post("/api/reconcile", json={"csv": csv_text})


def test_all_exception_classes_and_no_state_change(client):
    ids = [payment(client, f"order-{i}") for i in range(4)]
    for i in range(3):
        mark_succeeded(client, ids[i], f"event-{i}")
    csv_text = f"payment_id,amount_minor,currency\n{ids[0]},50000,INR\n{ids[1]},1,INR\n{ids[0]},50000,INR\nunknown,1,INR\n{ids[3]},50000,INR"
    result = reconcile(client, csv_text)
    assert result.status_code == 200
    body = result.json()
    assert body["matched"] == 1
    assert {f["kind"] for f in body["findings"]} == {"duplicate_settlement", "amount_mismatch", "unknown_payment", "status_mismatch", "missing_settlement"}
    assert client.get(f"/api/payments/{ids[1]}").json()["payment"]["status"] == "succeeded"


def test_complete_match_has_no_findings(client):
    pid = payment(client, "one")
    mark_succeeded(client, pid, "success")
    assert reconcile(client, f"payment_id,amount_minor,currency\n{pid},50000,INR").json() == {"rows": 1, "matched": 1, "findings": [], "scope": "all successful payments in this demo session"}


def test_missing_successful_payment_with_header_only(client):
    pid = payment(client, "one")
    mark_succeeded(client, pid, "success")
    result = reconcile(client, "payment_id,amount_minor,currency\n").json()
    assert result["findings"] == [{"payment_id": pid, "kind": "missing_settlement", "detail": "Successful payment is absent from this file."}]


@pytest.mark.parametrize("csv_text", [
    "bad,header\na,b",
    "payment_id,amount_minor,currency\nx,-1,INR",
    "payment_id,amount_minor,currency\nx,0,INR",
    "payment_id,amount_minor,currency\nx,1,USD",
    "payment_id,amount_minor,currency\nx,1,INR,extra",
    "payment_id,amount_minor,currency\nx,1",
    "payment_id,amount_minor,currency\nx,1.5,INR",
])
def test_malformed_csv_rejected(client, csv_text):
    assert reconcile(client, csv_text).status_code == 422


def test_other_session_payment_is_unknown_not_exposed(client):
    pid = payment(client, "one")
    mark_succeeded(client, pid, "success")
    client.headers["X-Demo-Session"] = "b" * 32
    result = reconcile(client, f"payment_id,amount_minor,currency\n{pid},50000,INR").json()
    assert [f["kind"] for f in result["findings"]] == ["unknown_payment"]
