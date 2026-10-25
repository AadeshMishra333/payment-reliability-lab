from fastapi.testclient import TestClient
import pytest

from app.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "event-tests.sqlite3")) as api:
        api.headers.update({"X-Demo-Session": "a" * 32, "Idempotency-Key": "order-1"})
        yield api


def make_payment(client, key="order-1"):
    return client.post("/api/payments", headers={"Idempotency-Key": key}, json={"amount_minor": 50000, "currency": "INR", "merchant_reference": key}).json()["payment"]["id"]


def send(client, pid, event_id="evt-1", status="succeeded"):
    return client.post(f"/api/payments/{pid}/events", json={"event_id": event_id, "status": status})


def test_success_event_is_recorded_and_survives_restart(tmp_path):
    path = tmp_path / "restart.sqlite3"
    with TestClient(create_app(path)) as first:
        first.headers.update({"X-Demo-Session": "a" * 32, "Idempotency-Key": "order-1"})
        pid = make_payment(first)
        event = send(first, pid)
        assert event.status_code == 200
        assert event.json()["applied"]
    with TestClient(create_app(path)) as restarted:
        restarted.headers["X-Demo-Session"] = "a" * 32
        detail = restarted.get(f"/api/payments/{pid}").json()
        assert detail["payment"]["status"] == "succeeded"
        assert [e["event_id"] for e in detail["events"]] == ["evt-1"]


def test_duplicate_event_has_no_second_effect(client):
    pid = make_payment(client)
    assert send(client, pid).json()["applied"]
    duplicate = send(client, pid)
    assert duplicate.status_code == 200 and duplicate.json()["replayed"]
    assert len(client.get(f"/api/payments/{pid}").json()["events"]) == 1


def test_changed_duplicate_event_and_cross_payment_reuse_conflict(client):
    first, second = make_payment(client), make_payment(client, "order-2")
    send(client, first)
    assert send(client, first, status="failed").status_code == 409
    assert send(client, second).status_code == 409
    assert client.get(f"/api/payments/{second}").json()["payment"]["status"] == "pending"


def test_late_pending_or_failed_event_cannot_regress_success(client):
    pid = make_payment(client)
    send(client, pid)
    assert send(client, pid, "late-pending", "pending").status_code == 409
    assert send(client, pid, "late-failed", "failed").status_code == 409
    assert client.get(f"/api/payments/{pid}").json()["payment"]["status"] == "succeeded"


def test_same_status_with_new_event_records_no_state_change(client):
    pid = make_payment(client)
    send(client, pid)
    result = send(client, pid, "evt-2", "succeeded")
    assert result.status_code == 200
    assert not result.json()["replayed"] and not result.json()["applied"]
    assert len(client.get(f"/api/payments/{pid}").json()["events"]) == 2


def test_events_require_same_session_as_payment(client):
    pid = make_payment(client)
    client.headers["X-Demo-Session"] = "b" * 32
    assert send(client, pid).status_code == 404


@pytest.mark.parametrize("event_id", ["", "bad event", "e" * 81])
def test_invalid_event_id_rejected(client, event_id):
    pid = make_payment(client)
    assert send(client, pid, event_id).status_code == 422
    assert client.get(f"/api/payments/{pid}").json()["events"] == []
