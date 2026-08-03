# The Republic Bulletin

A newspaper-style publishing platform with reader, journalist, editor, admin, and publisher desks. The frontend uses Next.js 16; the API uses FastAPI and SQLAlchemy.

## Local development

1. Copy `backend/.env.example` to `backend/.env`, set `ENVIRONMENT=development`, `COOKIE_SECURE=false`, and use a private development `SECRET_KEY`.
2. Copy `frontend/.env.example` to `frontend/.env.local` and set both URLs to the local services.
3. In `backend`, install `requirements-dev.txt` and run `uvicorn app.main:app --reload`.
4. In `frontend`, run `npm install` and `npm run dev`.

The default local URLs are `http://localhost:3000` and `http://localhost:8000`.

## Verification

- Frontend: `npm run lint` and `npm run build`
- Backend: `python -m unittest test_api.py`

The API test uses a temporary database and does not modify the development database.

## Production checklist

- Set a strong unique `SECRET_KEY`, `ENVIRONMENT=production`, and `COOKIE_SECURE=true`.
- Restrict `CORS_ORIGINS`, `CORS_ORIGIN_REGEX`, and `ALLOWED_HOSTS` to the deployed domains.
- Run the API behind TLS and a reverse proxy with request-size and rate limits.
- Use managed PostgreSQL and migrations for a multi-instance deployment; SQLite is intended for a single small instance.
- Back up the database and uploaded media, and send application logs to monitored storage.

## One-VM deployment

From the root of a fresh clone on an Ubuntu or Debian VM, point your domain DNS at the VM, open ports 80 and 443, then run:

```bash
sudo bash deploy.sh --domain news.example.com --email admin@example.com
```

The script installs Nginx, Python, Node.js 20, and Certbot; builds both applications; configures HTTPS; and starts the frontend and backend as systemd services. For a private VM without a domain, use `--http-only`. Back up `backend/news.db`, `backend/uploads`, and `backend/.env`.

After deployment, verify the backend at `https://your-domain/api/health` and browse its API documentation at `https://your-domain/api/docs`. The bare `/api` path intentionally returns `404` because it is not an API endpoint.
