# Simulated provider events

This endpoint is an internal teaching simulator. It is not a real payment-provider webhook and has no signature verification. Use synthetic data only.

`POST /api/payments/{payment_id}/events` requires the demo session header and accepts an `event_id` plus one status: `pending`, `succeeded`, or `failed`. The server writes the event and any payment-state change in one SQLite transaction. `GET /api/payments/{payment_id}` returns the event history in arrival order.

The initial state is `pending`. A pending payment can become `succeeded` or `failed`. A terminal state cannot change to a different state in this simulation. A new event that repeats the current state is recorded with `applied: false`. An identical repeat of the same event ID returns `replayed: true` without a second event row. Reusing an event ID for another payment or status returns HTTP `409`.

This state machine is deliberately small. It does not represent real refunds, reversals, chargebacks or disputes. The event ID is unique within one demo session. A valid session token is required to read or update its payment; demo tokens are not authenticated accounts.

## Explain-back exercise

Payment P is pending. Event E1 marks it succeeded. E1 arrives again, then event E2 says pending. Predict the HTTP response and database rows after each request. Point to the transaction and uniqueness rule that protect the result.
