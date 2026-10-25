# Build sequence and learning gates

This is a **plan**, not a completion log. The mature scope is approximately 100–135 active hours including 35–50 hours spent learning, tracing and explaining the system. At 9–12 hours per week it can fit roughly 12 weeks. At the previously saved 4 hours per week, plan for 25–34 weeks. Re-estimate after Aadesh states his actual availability. Do not backdate project experience.

## Product boundary

User: a merchant operator working with a small synthetic transaction set. Their questions are: Did this payment get recorded once? Why is its status pending? Does a settlement file match internal records? The system is a simulator and stores no real payment credentials or card data.

Stack direction: Python 3.11+, FastAPI and pytest. Use SQLite for the first working slice, then PostgreSQL after the transaction rules and data model are understood. Start the interface with accessible HTML/CSS/JavaScript; move to React/TypeScript if the state and interaction complexity justify it. Package with Docker, run checks in GitHub Actions and choose a host that provides persistent storage before a live demo. A hosting account has not yet been configured.

Progress as of 26 October 2026: steps 0–4 are implemented and assistant-tested locally; event and reconciliation endpoints have no browser controls yet. Aadesh chose to reuse the earlier AI-generated prototype with disclosure; his personal explanation checkpoints remain pending. Later rows remain planned.

| Step | What we build | Done when | What Aadesh must explain |
|---|---|---|---|
| 0. Scaffold | Repository, app startup, test command and architecture notes | `GET /health` and the startup test pass from a clean checkout | What Uvicorn, FastAPI and a route do; why a health response is a narrow check |
| 1. First vertical slice | Payment request schema, `POST /payments`, `GET /payments/{id}`, SQLite payments table and tiny form | A synthetic INR 500 payment survives a server restart; invalid amount is rejected; UI shows the response | Browser → HTTP → validation → function → SQL row → response; why integer paise avoid floating-point errors |
| 2. One intended operation | Idempotency key stored under a unique constraint; transaction around check/create | Same key and same payload return one payment; same key and changed payload give conflict; concurrent requests are tested | Lost response versus duplicate operation; what the DB constraint guarantees |
| 3. Event history | Simulated provider-event endpoint, event IDs and legal status transitions | Repeated identical event has no second effect; mismatched duplicate or illegal transition is rejected | At-least-once delivery; pending and terminal states; event ID scope |
| 4. Reconciliation | CSV import validation and exception report | Missing, unknown, duplicate and amount-mismatched rows are classified; no payment state changes | Why the exception report is read-only; matching and malformed input rules |
| 5. Operator UI | Payment table, detail timeline, idempotency replay feedback and reconciliation view | One user can complete the demo by browser; keyboard and error paths work | UI state versus durable server state; loading, retry and safe display of API errors |
| 6. Reliable asynchronous work | Outbox table and separate worker with bounded retries | Worker crash/restart test preserves the payment state; duplicate delivery does not duplicate effects | Why the outbox helps; where exactly-once claims fail |
| 7. Access and operations | Authenticated demo users, server-side access checks, request IDs, structured logs, useful metrics | A second user cannot read the first user's records; logs identify a failed request without exposing secrets | Identity versus current random demo token; access boundary; useful metrics versus a single health check |
| 8. Deployment and evidence | PostgreSQL migration, Docker image, CI, public demo, reproducible load exercise and documentation | Clean deploy with persistent storage; published setup; measured workload and failure notes | One SQL and one deployment tradeoff; a real failure and repair; limits of test results |

Milestones 1–5 target a credible small full-stack application. Steps 6–8 deepen operational and distributed-systems understanding. We will adjust ordering when a concrete failure or interview deadline makes another small slice more valuable. Optional Visa sandbox work is a separate experiment and would use only sandbox data.

## Working method for each step

1. Write the user action and expected response in one or two sentences.
2. Ask Aadesh to predict one edge case. Use his answer to decide how much explanation he needs.
3. Make the smallest working change, with a check that could fail for a real mistake.
4. Trace one request through code and data; inspect a failure case.
5. Have Aadesh change or explain one unseen variation. Record what was generated, inspected, tested and personally explained.
6. Only then update the README, evidence log and potential resume wording.

Claude Opus is useful for a focused frontend deliverable such as a single form or table after we have an API contract. Give it the exact contract, states and accessibility requirements. Review its output for network calls, hidden fake data, unsafe HTML injection and behavior inconsistent with backend tests. Do not merge a whole UI without tracing its request path.

## Next working session

Trace the implemented `POST /api/payments` and idempotency paths with Aadesh. Ask him to predict what happens if a database commit succeeds but the browser never receives the response; have him test a same-key retry and a changed-payload conflict. The next code milestone is simulated provider events and legal status transitions.
