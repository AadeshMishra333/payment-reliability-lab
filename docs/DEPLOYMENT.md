# Deploy the synthetic demo

The root `render.yaml` defines one free Render web service. The [public demo](https://payment-reliability-lab.onrender.com/) was deployed from the public repository's `main` branch on 26 October 2026. Its initial deploy passed Render's `/health` check. In the public browser, the assistant checked zero-amount validation, created a synthetic payment, retried its key, applied and replayed a simulated event, and compared a matching and mismatched settlement CSV. Use only fabricated data.

[Render's free web service filesystem is ephemeral](https://render.com/docs/free). SQLite records may disappear after a restart or deploy. This is acceptable only as an explicitly temporary learning demo. It is not durable payment storage. The free service may spin down when idle and take time to wake. A long-lived version needs a hosted database or a persistent disk on a paid service, plus stronger authentication and operations controls.

The service uses a single Uvicorn process because the local SQLite implementation was designed for one instance. Do not scale this version to multiple replicas. Its random browser session token limits accidental cross-session reads but is not a user account or production authentication.

The live URL is suitable as a temporary learning demo link. Explain the ephemeral storage and AI assistance when discussing the project; a successful deploy does not demonstrate personal code ownership or production readiness.
