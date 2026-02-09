# Productivity Control API

Backend for authentication, organizations, approvals, teams, tasks, sessions, activity events, and audit logs.

## Quick start

1) Create a virtual environment and install dependencies:

```
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

2) Copy and edit env file:

```
copy .env.example .env
```

3) Run the API:

```
uvicorn app.main:app --reload
```

## Notes

- Database tables are created on startup for now.
- Configure `DATABASE_URL` for PostgreSQL.
- Architecture overview: docs/ARCHITECTURE.md.
- API overview: docs/API.md.
- Recording storage is local by default; adjust `STORAGE_*` env vars.
