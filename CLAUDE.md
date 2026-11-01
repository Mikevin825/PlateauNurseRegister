# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Project Overview

Plateau State Nurse Registry and Licence Verification Platform: a four-day MVP for NANNM Plateau Chapter. Officers register nurses, supervisors review and approve records, approved nurses receive a printable ID card with a QR code, and the public verifies registration and licence status by NANNM ID or QR. Hospital HR gets a read-only, employer-scoped view. The demo must run on a laptop without Docker and remain usable immediately after the event.

The PRD is the source of truth: `.agents/PRDs/PRD.md`. Work items are `PNR-01` through `PNR-30` in `.agents/stories/plateau-nurse-register-stories.md` and GitHub issues on `ranocodes/PlateauNurseRegister`.

---

## Tech Stack

| Technology | Purpose |
|---|---|
| Python 3.12+ | Runtime |
| Django | Auth, admin, ORM, migrations, forms, email, test runner |
| Jinja2 template backend | Server-rendered registration, verification, and card pages |
| Django REST Framework | Thin `/api/v1/` API for a future Vite frontend |
| DRF TokenAuthentication | API auth; no JWT package |
| SQLite / PostgreSQL | SQLite for the laptop demo; PostgreSQL via `DATABASE_URL` when hosted |
| django-auditlog | Audit trail; no custom audit table |
| django-ratelimit | Public verification throttling |
| qrcode + Pillow | In-process QR generation |
| cryptography (Fernet) | NIN encryption at rest |
| django-environ | Environment configuration |
| WhiteNoise + Gunicorn | Optional VPS deployment |
| Django SMTP email backend | Expiry reminders through any SMTP provider |
| Django test runner | Smoke tests for core flows |

**Not used in the MVP:** Docker, Celery, Redis, S3/`django-storages`, WeasyPrint/xhtml2pdf, React/Next.js, Sentry, JWT packages.

**Dependency policy:** Django built-ins first. Add a maintained package only where Django has no built-in. Do not hand-roll audit, rate limiting, QR, encryption, or env parsing. Justify every new dependency.

---

## Commands

```bash
# Activate the existing environment
source .venv/bin/activate

# Development
python manage.py migrate
python manage.py runserver

# Tests
python manage.py test

# Demo data (planned)
python manage.py seed_demo

# Expiry reminders (planned)
python manage.py send_expiry_reminders

# Validation before committing
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Lint is optional and not configured yet. If `ruff` is added, run `ruff check .`.

---

## Architecture

```
config/                  # Django project settings and root URLs
registry/                # Core domain app
  models.py              # Nurse, LicenceDocument, Employer, Flag, Notification
  admin.py               # Review queue, actions, HR scoping, CSV export
  forms.py               # Registration and renewal forms
  views.py               # Registration, public verify, ID card, protected media
  services.py            # Approve, reject, flag, suspend, revoke, renew, status
  urls.py
  management/commands/   # seed_demo, send_expiry_reminders
  tests.py
api/                     # DRF serializers, views, URLs
templates/               # base.html, register.html, verify.html, card.html, email/
static/                  # Small hand-written CSS; no frontend framework
media/                   # Private uploads; never under the web root
manage.py
requirements.txt
.env.example
README.md
```

**Data flow:** Browser → Django session auth → custom views or Django admin → `services.py` for multi-step actions → ORM → SQLite/PostgreSQL. Public verification and the QR endpoint read the same minimal serializer. Email goes through Django's SMTP backend. Management commands run manually for the demo and by cron on a VPS.

**Current state:** only the `config/` scaffold exists. `registry/`, `api/`, `templates/`, `static/`, `requirements.txt`, and `.env.example` still need to be created. `db.sqlite3` is empty. Build in PRD phase order (Day 1 → Day 4).

---

## Code Patterns

### Django conventions
- Use Django built-ins: `User`, groups, permissions, sessions, admin, forms, ORM, migrations, email, test runner.
- Keep views thin. Put approve, reject, flag, suspend, revoke, renew, and status computation in `registry/services.py`.
- Wrap multi-step state changes in `transaction.atomic()`.
- Do not edit `record_status` directly in admin; expose admin actions only.
- Require a reason for every transition except `pending → approved`.
- Never store computed licence colour. Derive it from `licence_expiry` and `now()`.
- Use `TextChoices` for statuses and document types.

### Naming
- Python: `snake_case`; classes: `PascalCase`; constants: `UPPER_SNAKE_CASE`.
- Templates: `snake_case.html`; URL names: `snake_case`.
- NANNM ID format: `PLT-NUR-` plus a zero-padded sequence, e.g. `PLT-NUR-000417`. Immutable after issue.
- QR encodes `PUBLIC_BASE_URL/verify/<nanm_id>`. Generate on request; never store QR files.

### Permissions
- Groups: `Officer`, `Supervisor`, `Super Admin`, `HR`.
- HR scoping comes from `Employer.hr_users`; filter querysets, never trust a URL.
- Officers review. Only Supervisor and above approve renewals, suspend, or revoke.
- Super Admin alone exports CSV and sees the full audit log.

### Security
- Encrypt NIN with Fernet before saving; store `nin_encrypted` and `nin_last4` only. Never store plaintext.
- Reveal NIN only to Officer, Supervisor, or Super Admin; audit every reveal.
- Never expose NIN, licence number, phone, email, ward, or address publicly or to HR.
- Serve media only through permission-checked Django views. No public media URLs, no path traversal.
- Validate upload content type, extension, size, and image/PDF parsing server-side.
- Rate-limit public verification; keep the honeypot; no public list or search-by-name endpoint.
- Use `DEBUG=False` outside local demo. Secrets live in `.env`, never in the repo.
- Demo data must be fake. No real nurse PII.

### Templates and frontend
- Jinja2 backend, mobile-first, one column for forms.
- No React, Vue, or build step in the MVP.
- ID card uses a print stylesheet and the browser print dialog; no PDF library.
- Keep CSS small and hand-written.

### API
- Version under `/api/v1/`.
- DRF `TokenAuthentication`.
- Reuse `services.py`; do not duplicate business logic in API views.
- Public verification returns the same minimal fields as the web page.

### Status rules
- Stored: `pending`, `approved`, `rejected`, `flagged`, `suspended`, `revoked`.
- Computed colour: green > 180 days, yellow ≤ 180 days, red expired, grey pending, black flagged/suspended/revoked.
- Valid transitions: `pending → approved|rejected|flagged`; `approved → suspended|revoked`; `suspended → approved|revoked`; `flagged → approved|rejected|revoked`; `rejected → pending` on re-upload; `revoked` is terminal.

---

## Testing

- **Run:** `python manage.py test`
- **Location:** `registry/tests.py`, `api/tests.py`
- **Approach:** Django `TestCase`; cover registration, approval, public verification, HR scoping, renewal, reminders, audit, and CSV export.
- **Smoke path:** register → approve → print card → scan QR → verify → HR view → renewal → reminder → export.
- Tests must not depend on network access, real SMTP, or real PII.

---

## Validation

Run before committing:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Also confirm:
- No secrets, real NINs, or real nurse data are staged.
- `db.sqlite3` and `media/` are not committed.
- Privileged actions still write audit entries.
- The demo path still works end to end.

---

## Key Files

| File | Purpose |
|---|---|
| `config/settings.py` | Settings, env parsing, database switch, email, media |
| `config/urls.py` | Root URL configuration |
| `manage.py` | Django entry point |
| `.agents/PRDs/PRD.md` | Product requirements and data model |
| `.agents/stories/plateau-nurse-register-stories.md` | 30 implementation stories, dependencies, cut order |
| `.claude/commands/` | Project workflow commands |
| `.env.example` | Required environment variables (to create) |
| `requirements.txt` | Pinned dependencies (to create) |

---

## On-Demand Context

| Topic | File |
|---|---|
| Product scope, security, API, phases | `.agents/PRDs/PRD.md` |
| Story acceptance criteria and dependencies | `.agents/stories/plateau-nurse-register-stories.md` |
| Original interview notes | `.agents/PlateauNurseRegister.md` |
| GitHub epic and issues | `https://github.com/ranocodes/PlateauNurseRegister/issues` |

---

## Notes

- Four working days. Cut from the bottom of Day 3 if time slips. Never cut registration, approval, or public verification.
- Prefer the simplest thing that demos reliably. No infrastructure the laptop demo does not need.
- The installed environment currently has Django 6.1.2; the PRD targets Django 5.x. Pin a version in `requirements.txt` before adding dependencies.
- `settings.py` still uses the default `DjangoTemplates` backend; switch to Jinja2 as part of the scaffold work.
- Add `media/` to `.gitignore` when private uploads are introduced.
- Do not commit unless explicitly asked.
