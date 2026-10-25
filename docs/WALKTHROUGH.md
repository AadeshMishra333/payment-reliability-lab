# Explain the Payment Reliability Lab

## The real problem this simulates

A merchant sends a payment request and loses the HTTP response. It cannot know whether the server recorded the request. Retrying without a stable identifier might create a second payment. Later, a provider may deliver the same status notification twice. Finally, a settlement file may disagree with the merchant's internal records. This project makes those three failure cases visible with fabricated INR amounts. It never moves money or receives a real provider webhook.

## Trace one browser action

1. In `static/app.js`, the form converts rupees to integer paise, checks for zero, and sends `POST /api/payments` with `X-Demo-Session` and `Idempotency-Key` headers.
2. In `app/models.py`, Pydantic validates the payload, including positive integer paise and INR currency.
3. In `app/main.py`, the route opens a write transaction and looks for the request key within this demo session.
4. If the key already exists with the same amount, currency and reference, the server returns that row with `replayed: true`. A changed payload gets HTTP 409.
5. Otherwise, `app/storage.py` commits a `pending` payment in SQLite. The database unique constraint on `(session, request_key)` protects the invariant even when requests overlap.
6. The browser refreshes from `GET /api/payments` and displays the server record. Refreshing the page re-reads SQLite; it does not reconstruct payments from browser memory.

**Why integer paise?** ₹500.00 is stored as `50000`. Decimal money expressed as a binary floating-point number can introduce rounding surprises; exact integer minor units avoid that in this fixed INR example. The client converts input for convenience; the server checks the integer independently.

**Why a transaction?** It groups the lookup, limit check and insertion under SQLite's `BEGIN IMMEDIATE`. A concurrent request cannot both see a missing key and create two rows. The unique database constraint remains the final guard. This gives one database payment for one request key, not an exactly-once guarantee for a real bank transfer.

## Trace a simulated event

Select a payment and click **Mark succeeded**. The browser sends `POST /api/payments/{id}/events` with an event ID. The server finds the payment only within this demo session, checks whether that event ID was already seen, checks the state transition, then updates the payment and records the event in one transaction. Repeating the same event ID and payload returns `replayed: true` with no second effect. Reusing its ID with different content returns HTTP 409. A `succeeded` or `failed` payment cannot switch to the other terminal state in this simplified model.

This is a manually triggered event simulator. It does not receive authenticated provider webhooks, verify signatures, or call a payment network.

## Trace a settlement comparison

After one payment succeeds, click **Fill from successful payments**. The page creates CSV with `payment_id,amount_minor,currency`. `POST /api/reconcile` parses at most 100 rows and compares them with this session's payments. It reports matched rows plus `unknown_payment`, `status_mismatch`, `amount_mismatch`, `duplicate_settlement`, and `missing_settlement` findings. It does not change payment state.

Try changing `50000` to `49000`: the amount mismatch is reported. Remove the successful payment row: it appears as missing. Add a second identical row: it appears as a duplicate. A malformed header or zero amount gets HTTP 422.

## Five-minute demo script

1. Enter `0` rupees and submit. Explain the on-screen message and why the backend would also reject zero.
2. Enter `500.00`, create the payment, then submit again with the same key. Point out the same payment ID and `replayed` feedback.
3. Change the amount while retaining the key. Explain HTTP 409, then choose **Use new key** for a new operation.
4. Select a pending payment, send `succeeded`, then send the same event ID again. Explain the difference between a repeated delivery and a new event.
5. Fill and compare a settlement CSV; edit its amount to provoke an exception. Explain that reconciliation is read-only.

## Questions to answer without reading the notes

1. The database commits the payment, but the browser loses the response. What will a retry with the same key do? Which line of defense stops a duplicate under concurrency?
2. Why would a client-side zero check be insufficient on its own?
3. What does the demo-session token protect, and why is it not a user login?
4. Why does a repeated provider event need an event ID independent of the payment request key?
5. A `succeeded` payment is absent from the settlement CSV. Which exception appears, and why doesn't comparison change its status?
6. On a free host, the service restarts and the SQLite file disappears. Which earlier claim about persistence is now false? How would you change the storage architecture?

## Limits you should volunteer in an interview

The code is an assistant-implemented learning prototype. Aadesh chose the scope and the zero-amount UI behavior but has not yet demonstrated the data-flow explanation or made an independent code change. The app uses a random session token, not authenticated accounts. It has no real processor integration, provider signature verification, background outbox, durable hosted database or load measurement. The test count shows checked behavior, not production readiness. A hosted free demo would use ephemeral SQLite, so records can reset.
