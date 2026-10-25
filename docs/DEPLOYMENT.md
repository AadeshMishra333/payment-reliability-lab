# Deploy the synthetic demo

The root `render.yaml` defines one free Render web service. From a Render account, create a new Blueprint using this public repository and review the plan before creating the service. No account or hosted service has been set up yet. After deployment, check `/health`, create a positive-amount synthetic payment in the browser, retry its key, send a simulated event, and compare a settlement CSV. Use only fabricated data.

[Render's free web service filesystem is ephemeral](https://render.com/docs/free). SQLite records may disappear after a restart or deploy. This is acceptable only as an explicitly temporary learning demo. It is not durable payment storage. The free service may spin down when idle and take time to wake. A long-lived version needs a hosted database or a persistent disk on a paid service, plus stronger authentication and operations controls.

The service uses a single Uvicorn process because the local SQLite implementation was designed for one instance. Do not scale this version to multiple replicas. Its random browser session token limits accidental cross-session reads but is not a user account or production authentication.

Before sharing a resume demo URL, visit the deployed page and exercise the browser flow. The repository URL is public source evidence even while the live demo is pending.
