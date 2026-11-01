# Plan: PNR-01 Project Scaffold and Configuration

## Summary

Turn the bare `config/` scaffold into a runnable Django project with Jinja2 templates, `django-environ` configuration, a SQLite/PostgreSQL switch, a root landing page, and an empty `registry` app ready for PNR-02. No domain models, admin actions, or business logic yet.

## User Story

As a developer
I want a runnable Django project with Jinja2 templates, environment configuration, and a SQLite/PostgreSQL switch
So that the team can build and demo without Docker

## Metadata

| Field | Value |
|-------|-------|
| Type | NEW_CAPABILITY |
| Complexity | MEDIUM |
| Systems Affected | `config/`, `registry/` skeleton, `templates/`, `requirements.txt`, `.env.example`, `.gitignore`, `README.md` |
| GitHub Issue | #2 (PNR-01) |

---

## Patterns to Follow

### Naming

```python
# SOURCE: config/settings.py:16
BASE_DIR = Path(__file__).resolve().parent.parent
```

```python
# SOURCE: manage.py:9
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
```

- Python: `snake_case` functions and variables, `PascalCase` classes.
- URL names: `snake_case`.
- Template files: `snake_case.html`.

### Configuration

```python
# SOURCE: config/settings.py:33-40
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]
```

```python
# SOURCE: config/settings.py:76-81
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

- Keep one settings file for the MVP.
- Use `django-environ`; do not write a custom env parser.
- Do not hardcode secrets or production hosts.

### URLs

```python
# SOURCE: config/urls.py:20-22
urlpatterns = [
    path('admin/', admin.site.urls),
]
```

- Root URLconf stays `config.urls`.
- App URLs live in `registry/urls.py` and are included from the root.

### Tests

No test files exist yet. Create the first pattern in `registry/tests.py` using Django `TestCase` and `self.client`.

### Error Handling

No custom error pattern exists. Use Django's `ImproperlyConfigured` for missing production configuration; otherwise let Django render its standard errors.

---

## Files to Change

| File | Action | Purpose |
|------|--------|---------|
| `requirements.txt` | CREATE | Pin Django, Jinja2, django-environ, psycopg |
| `.env.example` | CREATE | Document required environment variables |
| `.gitignore` | UPDATE | Ignore `media/`, `staticfiles/`, local env files |
| `config/settings.py` | UPDATE | Env parsing, Jinja2, DB switch, static, registry app |
| `config/urls.py` | UPDATE | Include `registry.urls` at the root |
| `registry/__init__.py` | CREATE | Make `registry` a package |
| `registry/apps.py` | CREATE | App config for `registry` |
| `registry/views.py` | CREATE | Root landing page view |
| `registry/urls.py` | CREATE | Root route |
| `registry/tests.py` | CREATE | Root page smoke test |
| `templates/base.html` | CREATE | Jinja2 base layout |
| `templates/home.html` | CREATE | Landing page extending base |
| `README.md` | UPDATE | Minimal local setup commands |

---

## Tasks

Execute in order. Each task is atomic and verifiable.

### Task 1: Pin runtime dependencies

- **File**: `requirements.txt`
- **Action**: CREATE
- **Implement**:
  - `Django==5.2` (PRD target; see Risks)
  - `Jinja2` (Django does not install it)
  - `django-environ`
  - `psycopg[binary]` (required for `DATABASE_URL` PostgreSQL)
  - Pin the exact versions pip resolves; do not use ranges.
- **Mirror**: `CLAUDE.md:34` dependency policy.
- **Validate**: `.venv/bin/pip install -r requirements.txt` then `.venv/bin/python -m django --version`.

### Task 2: Document environment variables

- **File**: `.env.example`
- **Action**: CREATE
- **Implement**:
  - `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`
  - `DATABASE_URL` (commented, optional)
  - `PUBLIC_BASE_URL`, `REMINDER_DAYS`
  - `NIN_ENCRYPTION_KEY` placeholder
  - SMTP placeholders from PRD section 9
  - No real secrets; placeholders only.
- **Mirror**: PRD section 9 configuration table.
- **Validate**: Confirm every key used by `settings.py` appears in the file.

### Task 3: Ignore local runtime artifacts

- **File**: `.gitignore`
- **Action**: UPDATE
- **Implement**: Add `media/`, `staticfiles/`, and keep existing `.env`, `.venv`, `db.sqlite3` rules.
- **Validate**: `git check-ignore -v media/test.txt staticfiles/test.css`.

### Task 4: Configure settings

- **File**: `config/settings.py`
- **Action**: UPDATE
- **Implement**:
  - Load `.env` with `environ.Env.read_env(BASE_DIR / ".env")`.
  - `SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-local-demo-only")`.
  - `DEBUG = env.bool("DJANGO_DEBUG", default=False)`.
  - `ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])`.
  - `CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])`.
  - Database switch:
    ```python
    DATABASE_URL = env("DATABASE_URL", default="")
    if DATABASE_URL:
        DATABASES = {"default": env.db_url("DATABASE_URL")}
    else:
        DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
    ```
    Do not put the SQLite path inside a URL; the workspace path contains spaces.
  - Switch `TEMPLATES` to `django.template.backends.jinja2.Jinja2` with `DIRS=[BASE_DIR / "templates"]` and `APP_DIRS=True`.
  - Add `registry` to `INSTALLED_APPS`.
  - Add `STATIC_ROOT = BASE_DIR / "staticfiles"` and `STATICFILES_DIRS = [BASE_DIR / "static"]` when `static/` exists.
  - Add `PUBLIC_BASE_URL = env("PUBLIC_BASE_URL", default="http://localhost:8000")`.
  - Add `REMINDER_DAYS = env.int("REMINDER_DAYS", default=30)`.
  - Set `TIME_ZONE = "Africa/Lagos"` and keep `USE_TZ = True`.
  - Keep `DEFAULT_AUTO_FIELD`.
- **Mirror**: `config/settings.py:16`, `:33-40`, `:76-81`.
- **Validate**: `python manage.py check` with no `.env` and with `DJANGO_DEBUG=True`.

### Task 5: Create the registry app skeleton

- **Files**: `registry/__init__.py`, `registry/apps.py`, `registry/views.py`, `registry/urls.py`
- **Action**: CREATE
- **Implement**:
  - `RegistryConfig` with `name = "registry"`.
  - `home(request)` renders `home.html`.
  - `urlpatterns = [path("", views.home, name="home")]`.
  - Do not create models yet; PNR-02 owns `models.py` and migrations.
- **Mirror**: PRD directory structure and `CLAUDE.md:92`.
- **Validate**: `python manage.py check` and `python -c "import registry"`.

### Task 6: Add Jinja2 templates

- **Files**: `templates/base.html`, `templates/home.html`
- **Action**: CREATE
- **Implement**:
  - `base.html`: minimal mobile-first layout, `{% block content %}`, title block.
  - `home.html`: `{% extends "base.html" %}` with the registry name and a short landing message.
  - No CSS framework; inline or minimal markup only.
- **Mirror**: `CLAUDE.md:130` Jinja2 and mobile-first rule.
- **Validate**: `python manage.py runserver` and open `/`.

### Task 7: Wire root URLs

- **File**: `config/urls.py`
- **Action**: UPDATE
- **Implement**: Keep `admin/`, add `path("", include("registry.urls"))`.
- **Mirror**: `config/urls.py:20-22`.
- **Validate**: `python manage.py check` and `python manage.py show_urls` if available; otherwise request `/` in tests.

### Task 8: Add the root page smoke test

- **File**: `registry/tests.py`
- **Action**: CREATE
- **Implement**:
  - `HomePageTests(TestCase)`.
  - `test_home_page_renders`: `self.client.get("/")` returns `200`, uses `home.html`, contains the registry name.
  - `test_debug_defaults_to_false`: assert `settings.DEBUG is False` when `DJANGO_DEBUG` is unset.
- **Mirror**: Django `TestCase`; no existing test file.
- **Validate**: `python manage.py test registry`.

### Task 9: Add minimal local setup notes

- **File**: `README.md`
- **Action**: UPDATE
- **Implement**:
  - Activate `.venv`.
  - `pip install -r requirements.txt`.
  - `cp .env.example .env` and set a local secret.
  - `python manage.py migrate`.
  - `python manage.py runserver`.
- **Mirror**: `CLAUDE.md:40-58` commands.
- **Validate**: Follow the steps in a clean shell.

### Task 10: Full scaffold validation

- **Files**: none
- **Action**: VALIDATE
- **Implement**:
  - Run checks, migrations, tests, and the root request.
  - Confirm SQLite is used without `DATABASE_URL`.
  - Confirm a PostgreSQL `DATABASE_URL` selects the PostgreSQL backend (do not require a live server for `check`).
- **Validate**:
  ```bash
  source .venv/bin/activate
  python manage.py check
  python manage.py makemigrations --check --dry-run
  python manage.py test
  python manage.py migrate
  python manage.py runserver 127.0.0.1:8000
  curl -I http://127.0.0.1:8000/
  ```

---

## Validation

```bash
source .venv/bin/activate

# Dependencies
pip install -r requirements.txt

# Django checks
python manage.py check
python manage.py makemigrations --check --dry-run

# Tests
python manage.py test

# Database
python manage.py migrate

# Root page
python manage.py runserver 127.0.0.1:8000
curl -I http://127.0.0.1:8000/

# Environment branches
DJANGO_DEBUG=True python manage.py check
DATABASE_URL=postgres://user:pass@localhost:5432/registry python manage.py check
```

`python manage.py check` with a PostgreSQL URL validates settings only; it does not connect to a database.

---

## Risks

| Risk | Mitigation |
|------|------------|
| `.venv` has Django 6.1.2; PRD targets 5.x | Pin `Django==5.2` in `requirements.txt` and reinstall. If 5.2 cannot be installed, use the installed 6.1.2 and update the PRD/CLAUDE note in the same PR. |
| Workspace path contains spaces | Never build a SQLite URL from `BASE_DIR`; use the explicit `DATABASES` dict branch. |
| Jinja2 backend differs from Django templates | Use `{% extends %}`, `{% block %}`, `url()` and `static()` globals; do not use `{% load %}` tags. |
| `DEBUG=False` default blocks static files under `runserver` | Keep `DJANGO_DEBUG=True` in the local `.env`; production static serving arrives with WhiteNoise in PNR-29. |
| `ALLOWED_HOSTS` empty causes 400 with `DEBUG=False` | Default to `localhost,127.0.0.1`. |
| PostgreSQL driver missing | Include `psycopg[binary]` in `requirements.txt`. |
| PNR-02 expects an app that does not exist | Create the `registry` skeleton here; PNR-02 adds models and migrations only. |

---

## Acceptance Criteria

- [ ] A clean clone installs requirements and starts with `runserver`.
- [ ] Without `DATABASE_URL`, settings use SQLite at `db.sqlite3`.
- [ ] With `DATABASE_URL`, settings use the PostgreSQL backend.
- [ ] With `DJANGO_DEBUG` unset, `DEBUG` is `False`.
- [ ] `/` renders the Jinja2 `home.html` page extending `base.html`.
- [ ] `python manage.py check` passes.
- [ ] `python manage.py makemigrations --check --dry-run` passes.
- [ ] `python manage.py test` passes.
- [ ] No secrets, `.env`, `db.sqlite3`, `media/`, or `staticfiles/` are committed.
