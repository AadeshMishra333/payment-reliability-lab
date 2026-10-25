# Payment API contract — first working slice

Agreed behavior, 26 October 2026: an amount of zero is invalid. Show an **on-screen validation message to the person submitting the payment**. No email or account-holder messaging exists in this synthetic demo.

## Create a synthetic payment

`POST /api/payments`

```json
{"amount_minor": 50000, "currency": "INR", "merchant_reference": "ORDER-001"}
```

- `amount_minor`: positive integer paise, initially up to 10,000,000. Integer minor units avoid binary floating-point rounding of currency amounts.
- `currency`: `INR` for this first demo. We will not imply multi-currency support.
- `merchant_reference`: 1–80 nonblank characters after trimming. It is a merchant label, not a unique payment identifier.
- Unknown fields are rejected so a misspelled amount field cannot silently disappear.

Success: HTTP `201` with a server-generated payment ID, the submitted fields, `pending` status and creation time. The server persists the record to SQLite before returning it. The response does not imply real authorization or money movement.

Validation: HTTP `422` with a field-specific error. The UI displays a concise human message. Example: entering ₹0 shows **“Enter an amount greater than ₹0.00.”** No payment record is created. Negative, fractional-paise, missing and above-limit amounts are also rejected. Server validation is authoritative even if a browser input blocks the value locally.

## Read the payment

`GET /api/payments/{payment_id}` returns the stored payment or HTTP `404` if absent. `GET /api/payments` lists a bounded set of payments for the current demo session. We will keep synthetic sessions separate using a random browser-held token; this is demo isolation, not a production identity system.

## Later contract additions

Milestone 2 adds an `Idempotency-Key` request header. A matching retry will return the original payment; a changed payload with the same key will return HTTP `409`. This guarantee requires a database uniqueness rule and transaction. The first create/read milestone does not claim that behavior before the code and tests exist.

Milestone 3 adds simulated provider events. Milestone 4 adds read-only reconciliation. These are separate from the first working slice.

## Acceptance demonstration for milestone 1

1. Create a ₹500.00 payment and record its ID; read it back after restarting the server.
2. Submit ₹0.00 through the UI; see the agreed message, HTTP `422`, and no new row.
3. Submit a malformed amount directly to the API; see server rejection even without browser validation.
4. Trace the request from UI to schema, endpoint, SQL insert and HTTP response.
