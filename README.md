# PlateauNurseRegister

Plateau State Nurse Registry and Licence Verification Platform.

## Local setup

```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Put the generated value in NIN_ENCRYPTION_KEY in .env
python manage.py migrate
python manage.py setup_groups
python manage.py seed_demo
python manage.py runserver
```

Open the Vite app at `http://localhost:5173/`. The React staff sign-in is at `/admin/login`; Django administration is available at `/django-admin/`.

`NIN_ENCRYPTION_KEY` is required for registration and NIN reveal. Keep the same key for the life of the database; changing it makes existing encrypted NINs unreadable.

Password recovery is available from the nurse and hospital/HR sign-in pages. Gmail delivery uses `smtp.gmail.com:587` with TLS; set `EMAIL_HOST_USER` to the sending Gmail address and `EMAIL_HOST_PASSWORD` to a Google App Password (not the regular account password). Set `DEFAULT_FROM_EMAIL` to the same address and `FRONTEND_BASE_URL` to the public React app URL. Restart Django after changing these settings. If using another provider, replace the SMTP host and TLS settings with that provider's values.

## Demo data

`seed_demo` creates a fictional demonstration dataset: 18 nurses across 5 hospital employers, covering every registry scenario (approved, licence expiring, licence expired, pending, rejected, flagged, suspended, revoked, and confirmed/pending/rejected employment).

Everything is fake. Employer names end in `(Demo)`, licence numbers start with `PLT-LIC-DEMO-`, all email addresses use the reserved `example.test` domain, and photographs are generated placeholder images. No real nurse, employer or licence is represented.

The command is idempotent — running it again refreshes the records in place and creates no duplicates. Records that are not part of the demo dataset are left untouched.

```bash
python manage.py seed_demo            # create or refresh the demo dataset
python manage.py seed_demo --reset    # delete demo data first, then reseed
```

`--reset` also clears the superseded 60-record dataset produced by earlier versions of this command. Do not run it against a production database.

Nurses are created through the real registration form, moved between statuses through `registry.services.transition_nurse`, and have their employment decided through the real HR API endpoints, so the audit trail and status rules behave exactly as they do in normal use.

## Demo credentials

Every demo account uses the password `DemoPass123!`.

### Reviewer accounts

| Username | Role | Group |
|---|---|---|
| `demo_superadmin` | Super administrator | Super Admin |
| `demo_supervisor` | Registrar / reviewer | Supervisor |
| `demo_officer1` | Reviewer (legacy role) | Officer |

### Hospital HR accounts

| Username | Employer |
|---|---|
| `demo_hr1` | Plateau Specialist Hospital (Demo) |
| `demo_hr2` | Jos North General Hospital (Demo) |
| `demo_hr3` | Jos South Comprehensive Health Centre (Demo) |
| `demo_hr4` | Vom Christian Clinic (Demo) |
| `demo_hr5` | Pankshin Mission Hospital (Demo) |

### Nurse accounts

| Username | Email | Scenario |
|---|---|---|
| `demo_nurse1` | `amina.adamu@example.test` | Approved, licence valid |
| `demo_nurse2` | `grace.danjuma@example.test` | Approved, licence valid |
| `demo_nurse3` | `esther.musa@example.test` | Approved, employment pending |
| `demo_nurse4` | `faith.wuyep@example.test` | Approved, licence valid |

Sign in through the React app at `http://localhost:5173/admin/login` for reviewer accounts, `http://localhost:5173/hospital/login` for HR, or `http://localhost:5173/nurse/login` for the demo nurses. The Django admin site is separate at `http://127.0.0.1:8000/django-admin/`.

## Running the demonstration

The demo runs entirely on one laptop — no Docker and no deployed backend.

```bash
# terminal 1: backend
cd ~/Desktop/Coding/plateau-nurse-registry-backend
source .venv/bin/activate
python manage.py runserver

# terminal 2: frontend
cd ~/Desktop/Coding/plateau-nurse-registry
npm run dev
```

| Surface | URL |
|---|---|
| React app (use this) | http://localhost:5173 |
| Django REST API | http://127.0.0.1:8000/api/v1/ |
| Django admin | http://127.0.0.1:8000/django-admin/ |
| Public verification | http://127.0.0.1:8000/verify/ |

Vite proxies `/api/v1` to the backend, so the browser only ever talks to `localhost:5173`.

### Suggested flow

1. **Public verification** — open `/verify/` and enter the NANNM ID printed by `seed_demo` (the *Public verification example* line), or copy any ID from the reviewer's nurse list. Then look up a suspended and a revoked record the same way.
2. **Reviewer** — sign in at `/admin/login` as `demo_supervisor`. The dashboard shows 20 nurses, 4 pending, 2 expired, 2 restricted and 1 pending renewal. Approve a pending record to see a NANNM ID issued.
3. **Hospital HR** — sign in at `/hospital/login` as `demo_hr1`. Only the 6 Plateau Specialist Hospital nurses appear. Under *Employment Verification*, confirm or reject a pending claim.
4. **Nurse** — sign in at `/nurse/login` as `demo_nurse1` and open *Digital ID Card* to see the photo, QR code and licence status. `demo_nurse3` shows the employment-pending state.

`demo_hr2`–`demo_hr5` each see only their own hospital, which demonstrates employer scoping.

To refresh the dataset after experimenting:

```bash
python manage.py seed_demo --reset
```

The demonstration data lives in the local `db.sqlite3`. A deployed frontend such as the Vercel preview cannot reach it — serving the demo requires running the backend on the same machine, or deploying the backend separately and pointing `VITE_API_BASE_URL` at it.

## Checks

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```


## Production routing

Build the React app in `../plateau-nurse-registry` with `npm run build` and serve its `dist` directory. `deploy/nginx.conf.example` shows a same-origin Nginx setup: React deep links fall back to `index.html`, `/api/v1/` and `/django-admin/` go to Django, and `/media/` is not exposed directly. Registry photos are delivered by the public verification API; uploaded licence documents require an authenticated reviewer.

For production, configure a strong unique `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, `ALLOWED_HOSTS`, `FRONTEND_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, HTTPS, secure cookie flags, and a positive `SECURE_HSTS_SECONDS`. Set `VITE_API_BASE_URL=/api/v1` for same-origin hosting. Use a shared Redis `CACHE_URL` in production so login rate limits work across workers, and set `RATELIMIT_IP_META_KEY=HTTP_X_REAL_IP` only when a trusted reverse proxy overwrites that header (as in the Nginx example). Replace the example hostname, certificate paths, and Django upstream in the Nginx file before deployment.
