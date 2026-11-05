import time
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.storage import PaymentStore
from app.operations import dispatch_one, enqueue, migrate

@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path/'ops.db')) as c:
        c.headers['X-Demo-Session'] = 'a'*32
        yield c

def saved(client):
    return client.post('/api/runs', json={'csv':'payment_id,amount_minor,currency\nunknown,100,INR'}).json()

def test_reupload_is_snapshot_and_does_not_duplicate_cases(client):
    first = saved(client)
    second = saved(client)
    assert first['id'] == second['id'] and second['replayed']
    ops = client.get('/api/operations').json()
    assert len(ops['cases']) == len(ops['jobs']) == 1
    assert client.get('/api/payments').json()['payments'] == []

def test_resolution_audit_and_stale_write(client):
    saved(client)
    case = client.get('/api/operations').json()['cases'][0]
    data = {'status':'resolved','note':'Checked synthetic file','version':0}
    assert client.patch('/api/cases/'+case['id'], json=data).status_code == 200
    assert client.patch('/api/cases/'+case['id'], json=data).status_code == 409
    latest = client.get('/api/operations').json()['cases'][0]
    assert latest['status'] == 'resolved' and len(latest['audit']) == 1
    assert client.patch('/api/cases/'+case['id'], json={**data,'status':'open','version':1}).status_code == 200

def test_operations_are_session_scoped(client):
    saved(client)
    case = client.get('/api/operations').json()['cases'][0]
    client.headers['X-Demo-Session'] = 'b'*32
    assert client.get('/api/operations').json() == {'runs':[], 'cases':[], 'jobs':[]}
    assert client.patch('/api/cases/'+case['id'], json={'status':'resolved','note':'Not mine','version':0}).status_code == 404

def test_saved_runs_survive_app_restart(tmp_path):
    path = tmp_path/'restart.db'
    for i in range(2):
        with TestClient(create_app(path)) as c:
            c.headers['X-Demo-Session'] = 'a'*32
            if not i: saved(c)
            else: assert len(c.get('/api/operations').json()['runs']) == 1

def test_concurrent_upload_creates_one_run(client):
    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(lambda _:saved(client)['id'], range(8)))
    assert len(set(ids)) == 1

def queued(tmp_path):
    s = PaymentStore(tmp_path/'worker.db'); migrate(s)
    with s.connect(write=True) as c: enqueue(c, 'a'*32, {'type':'test'})
    return s

def test_crash_after_delivery_recovers_without_duplicate_effect(tmp_path):
    s = queued(tmp_path); now = time.time()+1
    with pytest.raises(RuntimeError): dispatch_one(s, crash_after_delivery=True, now=now)
    assert not dispatch_one(s, now=now+1)
    assert dispatch_one(s, now=now+31)
    with s.connect() as c:
        assert c.execute('SELECT COUNT(*) FROM receipts').fetchone()[0] == 1
        assert c.execute('SELECT delivered,attempts FROM outbox').fetchone()[:] == (1,2)

def test_bounded_retry_exhaustion(tmp_path):
    s = queued(tmp_path); now=time.time()+1
    for i in range(5): assert dispatch_one(s, fail=True, now=now+i*100)
    assert not dispatch_one(s, now=now+600)
    with s.connect() as c:
        assert c.execute('SELECT failed,attempts FROM outbox').fetchone()[:] == (1,5)
        assert c.execute('SELECT COUNT(*) FROM receipts').fetchone()[0] == 0

def test_invalid_csv_does_not_save_partial_run(client):
    assert client.post('/api/runs', json={'csv':'broken'}).status_code == 422
    assert client.get('/api/operations').json()['runs'] == []
