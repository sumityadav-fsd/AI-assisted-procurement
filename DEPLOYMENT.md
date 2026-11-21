# Deployment — Vinayak ProcureAI

## Required environment variables

- `SARVAM_API_KEY`: required for live Sarvam AI calls.
- `AI_USE_CACHED_SAMPLES=false`: keep disabled; cached responses are not used by default.
- `DATA_PACK_DIR`: absolute path to an authorised private mount containing the Vinayak data pack.
- `DATABASE_PATH`: persistent writable SQLite path (or migrate to managed PostgreSQL before multi-instance production use).
- `UPLOAD_DIR`: persistent writable upload directory.

## Render / generic Python host

Build command:

```bash
python -m pip install -r backend/requirements.txt
```

Start command:

```bash
python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT
```

Set the environment variables in the hosting dashboard. Do not put API keys in source control.

## Private-data restriction

The supplied Vinayak data-pack README says these working documents must not be shared outside the hackathon team and must not be posted or retained after the hackathon; obtain permission before portfolio use. Therefore, **do not deploy this ZIP with `data_private/` to a public service or public repository**. Deploy the application code separately and mount the data pack only in an access-controlled environment with Vinayak's permission. If that permission is unavailable, deploy without the private pack and test with documents you are authorised to use.

## Operational limitation

This is a hackathon MVP, not production procurement software. SQLite and local file uploads need persistent storage. Add authentication, role-based access, audit retention policy, encrypted document storage, backups, malware scanning, rate limits and a production database before real organisational use.
