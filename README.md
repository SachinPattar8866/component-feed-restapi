Playto Challenge — Backend

Quick start (copy-paste ready)

1) Clone the repo and change into the backend folder

```powershell
git clone <your-repo-url>
cd backend
```

2) Create & activate a virtual environment (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

(Or on macOS / Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3) Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

4) Create a local `.env` from the example and update values

```powershell
copy .env.example .env
# then edit .env with a text editor and set SECRET_KEY, DEBUG=True (for local), etc.
```

Important env vars to check in `.env`:
- SECRET_KEY  (set a long random string)
- DEBUG  (True or False)
- DATABASE_URL  (optional — if empty app uses SQLite locally)
- ALLOWED_HOSTS  (comma separated, e.g. 'localhost,127.0.0.1')
- CORS_ALLOW_ALL_ORIGINS  (True for local testing)

5) Run database migrations and create an admin (optional)

```powershell
python manage.py migrate
python manage.py createsuperuser
```

6) Run the development server

```powershell
python manage.py runserver
# then visit http://127.0.0.1:8000
```

7) Useful commands

- Run tests:

```powershell
python manage.py test
```

- Collect static files (for production):

```powershell
python manage.py collectstatic --noinput
```

Production start (example used on Render)

```bash
bash -lc "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn config.wsgi --bind 0.0.0.0:$PORT"
```

Troubleshooting

- If you see a psycopg import error on deploy, ensure `requirements.txt` uses `psycopg[binary]>=3.0`.
- If frontend can't reach backend in production, ensure the frontend `VITE_API_BASE_URL` matches the backend URL and redeploy the frontend (Vite bakes env at build time).

API Quick reference

- POST /api/token/  — obtain JWT access & refresh (payload: {username, password})
- POST /api/users/  — register (if enabled)
- GET /api/posts/  — list posts
- POST /api/posts/  — create post (authenticated)
- POST /api/comments/  — add comment
