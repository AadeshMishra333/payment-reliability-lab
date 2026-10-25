# Architecture decisions

## 2026-10-26: Build from a clean scaffold

The workspace contains an earlier AI-generated, assistant-tested prototype at `work/visa/generated-payment-prototype-2026-10-26/`. It is preserved as a private reference and is **not** the source of this working repository. Starting from a small scaffold lets Aadesh own the contract and trace every new behavior. The earlier assistant's 22 passing tests are evidence about that separate reference prototype only.

## 2026-10-26: One service and a local database first

FastAPI and SQLite support a quick request-to-row trace with few moving parts. SQLite is suitable for a local, single-instance learning slice. Before a shared hosted demo, choose persistent storage and revisit transaction/concurrency behavior with PostgreSQL. Do not infer production scale or resilience from the local prototype.

## 2026-10-26: Add the frontend after the API contract

The initial screen will use semantic HTML and plain JavaScript. A React/TypeScript interface is optional if it simplifies later state management. Claude Opus may produce an isolated draft once we have a concrete API contract and loading/error states to test.
