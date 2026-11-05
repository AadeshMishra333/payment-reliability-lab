"""Saved investigations and a transactional outbox for synthetic notifications."""
import hashlib
import json
import time
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.models import ReconciliationInput
from app.reconciliation import compare, parse_csv

Session = Annotated[str, Header(alias="X-Demo-Session", pattern=r"^[a-f0-9]{32}$")]


def migrate(store):
    # Additive, idempotent schema upgrade: old payments and events are preserved.
    with store.connect(write=True) as c:
        for sql in [
            "CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, session TEXT NOT NULL, fingerprint TEXT NOT NULL, result TEXT NOT NULL, created_at REAL NOT NULL, UNIQUE(session,fingerprint))",
            "CREATE TABLE IF NOT EXISTS cases(id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), session TEXT NOT NULL, finding TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','resolved')), version INTEGER NOT NULL DEFAULT 0)",
            "CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id), session TEXT NOT NULL, status TEXT NOT NULL, note TEXT NOT NULL, created_at REAL NOT NULL)",
            "CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY, session TEXT NOT NULL, payload TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, available_at REAL NOT NULL, delivered INTEGER NOT NULL DEFAULT 0, failed INTEGER NOT NULL DEFAULT 0)",
            "CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY, session TEXT NOT NULL, payload TEXT NOT NULL, created_at REAL NOT NULL)",
            "CREATE INDEX IF NOT EXISTS cases_session ON cases(session)",
            "CREATE INDEX IF NOT EXISTS outbox_ready ON outbox(delivered,failed,available_at)",
            "PRAGMA user_version = 2",
        ]:
            c.execute(sql)


def enqueue(c, session, payload):
    c.execute("INSERT INTO outbox(id,session,payload,available_at) VALUES(?,?,?,?)",
              (uuid.uuid4().hex, session, json.dumps(payload), time.time()))


def dispatch_one(store, *, fail=False, crash_after_delivery=False, now=None):
    """At-least-once local delivery; receipt's primary key deduplicates effects.

    The claim lease expires after 30 seconds. Delivery and acknowledgement are
    deliberately separate commits so tests can reproduce the crash window.
    """
    now = time.time() if now is None else now
    with store.connect(write=True) as c:
        c.execute("UPDATE outbox SET failed=1 WHERE delivered=0 AND attempts>=5 AND available_at<=?", (now,))
        row = c.execute("SELECT * FROM outbox WHERE delivered=0 AND failed=0 AND attempts<5 AND available_at<=? ORDER BY available_at LIMIT 1", (now,)).fetchone()
        if row is None:
            return False
        c.execute("UPDATE outbox SET attempts=attempts+1,available_at=? WHERE id=?", (now + 30, row['id']))
    if fail:
        with store.connect(write=True) as c:
            c.execute("UPDATE outbox SET available_at=?,failed=? WHERE id=?", (now + min(2 ** (row['attempts'] + 1), 60), int(row['attempts'] + 1 >= 5), row['id']))
        return True
    with store.connect(write=True) as c:
        c.execute("INSERT OR IGNORE INTO receipts(id,session,payload,created_at) VALUES(?,?,?,?)", (row['id'], row['session'], row['payload'], now))
    if crash_after_delivery:
        raise RuntimeError("Injected crash after delivery, before acknowledgement")
    with store.connect(write=True) as c:
        c.execute("UPDATE outbox SET delivered=1 WHERE id=?", (row['id'],))
    return True


class Resolution(BaseModel):
    status: Literal['open', 'resolved']
    note: str = Field(min_length=3, max_length=500)
    version: int = Field(ge=0)

    @field_validator('note')
    @classmethod
    def meaningful_note(cls, value):
        if len(value.strip()) < 3:
            raise ValueError('Add an investigation note.')
        return value.strip()


def router(store):
    api = APIRouter(prefix='/api')

    @api.post('/runs')
    def create_run(data: ReconciliationInput, session: Session):
        records = parse_csv(data.csv)
        fingerprint = hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()
        with store.connect(write=True) as c:
            old = c.execute('SELECT * FROM runs WHERE session=? AND fingerprint=?', (session, fingerprint)).fetchone()
            if old:
                return {'id': old['id'], 'replayed': True, **json.loads(old['result'])}
            if c.execute('SELECT COUNT(*) FROM runs WHERE session=?', (session,)).fetchone()[0] >= 50:
                raise HTTPException(409, 'Demo limit: 50 saved runs per session.')
            payments = {r['id']: dict(r) for r in c.execute('SELECT * FROM payments WHERE session=?', (session,))}
            result = compare(records, payments)
            rid = 'run_' + uuid.uuid4().hex[:16]
            c.execute('INSERT INTO runs VALUES(?,?,?,?,?)', (rid, session, fingerprint, json.dumps(result), time.time()))
            for finding in result['findings']:
                c.execute('INSERT INTO cases(id,run_id,session,finding) VALUES(?,?,?,?)', ('case_' + uuid.uuid4().hex[:16], rid, session, json.dumps(finding)))
            enqueue(c, session, {'type': 'reconciliation.completed', 'run_id': rid, 'exceptions': len(result['findings'])})
        return {'id': rid, 'replayed': False, **result}

    @api.get('/operations')
    def operations(session: Session):
        with store.connect() as c:
            runs = [dict(r) for r in c.execute('SELECT id,fingerprint,created_at,result FROM runs WHERE session=? ORDER BY created_at DESC', (session,))]
            cases = [dict(r) for r in c.execute('SELECT * FROM cases WHERE session=? ORDER BY rowid DESC', (session,))]
            for case in cases:
                case.pop('session')
                case['finding'] = json.loads(case['finding'])
                case['audit'] = [dict(r) for r in c.execute('SELECT status,note,created_at FROM audit WHERE case_id=? AND session=? ORDER BY id', (case['id'], session))]
            for run in runs:
                run['result'] = json.loads(run['result'])
            jobs = [dict(r) for r in c.execute('SELECT id,attempts,delivered,failed FROM outbox WHERE session=?', (session,))]
        return {'runs': runs, 'cases': cases, 'jobs': jobs}

    @api.patch('/cases/{case_id}')
    def resolve(case_id: str, data: Resolution, session: Session):
        with store.connect(write=True) as c:
            case = c.execute('SELECT * FROM cases WHERE id=? AND session=?', (case_id, session)).fetchone()
            if not case:
                raise HTTPException(404, 'Case not found.')
            if case['version'] != data.version:
                raise HTTPException(409, 'Case changed. Refresh and review its latest history.')
            if c.execute('SELECT COUNT(*) FROM audit WHERE case_id=?', (case_id,)).fetchone()[0] >= 50:
                raise HTTPException(409, 'Demo limit: 50 updates per case.')
            c.execute('UPDATE cases SET status=?,version=version+1 WHERE id=?', (data.status, case_id))
            c.execute('INSERT INTO audit(case_id,session,status,note,created_at) VALUES(?,?,?,?,?)', (case_id, session, data.status, data.note, time.time()))
        return {'status': data.status, 'version': data.version + 1}

    return api
