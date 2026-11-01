# Product Requirements Document: Plateau State Nurse Registry and Licence Verification Platform

**Version:** 2.0 (4-day MVP)
**Status:** Draft
**Date:** 1 November 2026
**Owner:** NANNM Plateau Chapter (proposed data controller)
**Source:** `.agents/PlateauNurseRegister.md` (interview notes, 31 Oct 2026)
**Success measure:** A working demo that judges or the council can use immediately, and that can be run again after the event without a rebuild

---

## 1. Executive Summary

The Plateau State office of the National Association of Nigerian Nurses and Midwives (NANNM) lost its devices and paper records in an armed robbery. No register of nurses in the state survives. Hospitals cannot confirm whether a nurse is licensed, expired, or impersonating someone else.

This product is a secure nurse registry and licence verification platform. Officers register nurses on ward drives, supervisors review and approve records, and anyone can verify a nurse by NANNM ID or QR scan. The public sees minimal data; hospital HR sees an expanded profile; every privileged action is audited. Licence status is computed from the expiry date on the uploaded licence, never from a hardcoded validity period.

The build target is four days, not four weeks. The MVP is a working Django application that runs on a laptop with no Docker, uses seeded realistic data for the demo, and can be moved to a VPS or managed host later by changing environment variables. It uses Django built-ins wherever they exist and established packages only where Django has no equivalent. Internal admin work happens in Django admin. Custom screens are limited to officer registration, public verification, and the printable ID card.

---

## 2. Mission

**Mission:** Give Plateau State a nurse register that survives theft, fire, and disaster, and make licence status verifiable in seconds.

### Core Principles

1. **The record must outlive the device.** Data lives in a database with an export path, not on one laptop.
2. **Verify, do not assume.** Licence status comes from the uploaded expiry date and officer review. Nothing is hardcoded.
3. **Minimum disclosure.** The public sees the least data needed to confirm a nurse. NIN is never public and never shown to HR.
4. **Every action is attributable.** Privileged actions are logged with actor, time, and reason.
5. **Flag, notify, escalate.** The system surfaces status; a human decides enforcement.
6. **Boring technology, smallest scope.** Django built-ins first, proven packages second, custom code last.
7. **No vendor lock-in.** SMTP email, standard PostgreSQL or SQLite, and a plain Django app. Any host can run it.

---

## 3. Target Users

| Persona | Description | Technical Comfort | Key Needs | Pain Points |
|---|---|---|---|---|
| **Nurse** | Registered nurse or midwife in Plateau State | Low to moderate | Be registered once, prove identity, get an ID, receive expiry reminders | No existing record; fears impersonation; misses expiry |
| **Field Officer** | NANNM staff running ward-by-ward drives | Moderate | Register nurses quickly, capture documents and selfie, work a review queue | Paper forms, duplicates, slow review |
| **Supervisor** | Senior NANNM officer | Moderate | Resolve flagged cases, suspend or revoke IDs | No visibility into officer decisions |
| **Super Admin** | System owner / NANNM IT lead | High | Manage users, export data, view audit log, configure system | No system of record |
| **Hospital HR** | Approved HR staff at hospitals | Moderate | Confirm employment, check a nurse's verified profile | Cannot tell fake from real |
| **Public** | Patients, families, employers | Low | Verify a nurse by ID or QR in seconds | No way to check; impersonation goes undetected |

**MVP simplification:** nurses do not log in. Officers register them and officers upload renewals. This removes a whole authentication and self-service surface from the 4-day build.

---

## 4. MVP Scope

### In Scope

#### Core Functionality
- [x] Officer-assisted nurse registration (single form)
- [x] Consent checkbox with timestamp
- [x] Profile fields: full name, phone, email, NIN, licence number, licence expiry, employer, ward, specialty/cadre
- [x] Licence scan upload and live selfie capture
- [x] Officer review queue in Django admin: approve, reject with reason, flag
- [x] Unique NANNM ID issued on approval
- [x] QR code and printable ID card (browser print, no PDF library)
- [x] Public verification by NANNM ID or QR scan
- [x] HR login with employer-scoped read-only view and employment confirmation
- [x] Licence status computed from expiry date (green/yellow/red/grey/black)
- [x] One expiry reminder email, sent by a management command over real SMTP
- [x] Renewal: officer uploads new licence, supervisor approves, expiry updates
- [x] Suspension and revocation of NANNM ID, with reason
- [x] Audit log via `django-auditlog`, viewed in Django admin
- [x] CSV export via a Django admin action (super admin only)
- [x] Seeded realistic fake data for the demo
- [x] Thin REST API for core records, ready for a future Vite frontend

#### Technical
- [x] Django 5 with Jinja2 templates
- [x] SQLite by default for laptop demo; PostgreSQL via `DATABASE_URL` for deployment
- [x] Django built-in auth, groups, permissions, sessions, admin, forms, cache, and email
- [x] Local media storage outside the web root, served through permission-checked views
- [x] `django-auditlog` for audit history
- [x] `django-ratelimit` for public verification throttling
- [x] `qrcode` for QR generation
- [x] `cryptography` for NIN encryption
- [x] `django-environ` for configuration
- [x] WhiteNoise and Gunicorn for optional VPS deployment
- [x] No Docker requirement for the demo

#### Out of Scope
- [ ] Nurse self-registration and nurse login
- [ ] Offline-capable PWA and IndexedDB sync queue
- [ ] Vite frontend rewrite (React, Vue, or Svelte)
- [ ] Automated facial recognition or NIN API verification
- [ ] Direct NMCN API integration
- [ ] Automated enforcement of expired or fake licences
- [ ] SMS or WhatsApp reminders
- [ ] Bulk printed ID card fulfilment (on-site printing is in scope)
- [ ] Payments or renewal fees
- [ ] Multi-state or multi-tenant deployment
- [ ] Configurable status thresholds in the database (constants in settings for MVP)
- [ ] Separate 90-day and 30-day reminder schedules (one reminder type for MVP)
- [ ] S3 storage (local media for MVP; S3 is a post-demo upgrade)
- [ ] Docker (optional later; not needed for the laptop demo)
- [ ] Custom admin dashboard (Django admin covers it)
- [ ] Employment history (current employer only for MVP)
- [ ] Bulk historical data import from paper records
- [ ] Celery, Redis, or a separate search service

---

## 5. User Stories

### US-01: Officer registers a nurse
**As a** field officer, **I want to** register a nurse in one form with details, NIN, licence scan, and selfie, **so that** the nurse enters the register without needing a smartphone or account.

*Example:* At Plateau Specialist Hospital, an officer enters Adaeze's details, captures her NIN, photographs her licence (`NMCN/RN/123456`, expiry `2028-03-14`), takes a selfie, selects the employer and Ward 4, and submits. The record is `pending` and linked to the officer.

### US-02: Officer reviews and decides
**As an** officer, **I want to** compare the licence scan, selfie, and entered details against NMCN records, **so that** only genuine nurses are approved.

*Example:* The officer opens the pending record in Django admin, sees the scan and selfie side by side, checks NMCN manually, and chooses Approve. The system issues `PLT-NUR-000417`. If the scan is unreadable, the officer rejects with reason "Illegible licence scan — re-upload required".

### US-03: Public verification
**As a** member of the public, **I want to** enter a NANNM ID or scan a QR code, **so that** I can confirm a nurse is registered and licensed.

*Example:* A patient scans the QR on a nurse's printed card. The page shows name, photo, "Licensed", expiry, and employer name. An unknown ID returns "Not registered". NIN and licence number are never shown.

### US-04: HR verification
**As** hospital HR, **I want to** log in and see the full verified profile of nurses at my hospital, **so that** I can confirm employment and licence status.

*Example:* HR at Bingham University Teaching Hospital logs in, sees only nurses linked to their employer, opens a profile, and confirms employment. NIN is hidden.

### US-05: Expiry reminder
**As a** nurse, **I want to** receive an email before my licence expires, **so that** I can renew with NMCN.

*Example:* The daily command finds a licence expiring in 30 days, sends one email to the nurse, records the notification, and does not send again for the same expiry date.

### US-06: Renewal
**As an** officer, **I want to** upload a nurse's renewed licence and have a supervisor approve it, **so that** the expiry updates and the status returns to green.

*Example:* The officer adds a renewal document with expiry `2031-02-28`. The supervisor approves it in admin. The nurse's expiry updates, the old document remains in history, and the public status turns green.

### US-07: Flag and revoke
**As a** supervisor, **I want to** resolve flagged cases and suspend or revoke an ID, **so that** suspected impersonation is contained.

*Example:* An officer flags a nurse because the licence number belongs to another name. The supervisor investigates, records a reason, and revokes the NANNM ID. The public page shows "Revoked". The action is audited.

### US-08: Audit and export
**As a** super admin, **I want to** view the audit log and export the register as CSV, **so that** I can answer disputes and hand data to the council.

*Example:* The super admin filters audit entries by actor and exports a CSV of all licensed nurses. The export is itself audited.

### US-09: Demo reset
**As a** presenter, **I want** a single command that seeds realistic fake nurses, **so that** the demo is repeatable after the event.

*Example:* `python manage.py seed_demo` creates employers, staff, HR users, 60 nurses across all statuses, and placeholder scans and selfies.

### Technical User Stories

### US-T1: Thin API for a future Vite frontend
**As a** frontend developer, **I want** versioned endpoints for registration, verification, and licences, **so that** the Jinja frontend can later be replaced with a Vite app without changing the backend.

### US-T2: Laptop-first, host-anywhere
**As a** developer, **I want** the app to run with `runserver` and SQLite, **so that** the demo does not depend on Docker or a cloud account.

---

## 6. Core Architecture and Patterns

### High-Level Architecture

```
Browser (Jinja templates, mobile-friendly)
        |
        | HTTPS, Django session auth
        v
Django application (single process, Gunicorn on VPS)
  - Custom views: registration, public verify, ID card
  - Django admin: review queue, flags, users, audit, CSV export
  - REST API (/api/v1/, DRF)
  - Django auth, groups, permissions
        |
        +--> SQLite (laptop demo) or PostgreSQL (deployment)
        +--> Local media folder (licence scans, selfies, QR)
        +--> SMTP server via Django's built-in email backend
        +--> Optional Slack webhook for admin alerts

Management commands (run manually or by cron)
  - seed_demo
  - send_expiry_reminders
```

### Directory Structure

```
plateau-nurse-register/
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── registry/
│   ├── models.py          # Nurse, LicenceDocument, Employer, Flag, Notification
│   ├── admin.py           # Review queue, actions, HR scoping, CSV export
│   ├── forms.py           # Registration and renewal forms
│   ├── views.py           # Registration, public verify, ID card
│   ├── services.py        # Approval, revocation, renewal, status computation
│   ├── urls.py
│   ├── management/commands/
│   │   ├── seed_demo.py
│   │   └── send_expiry_reminders.py
│   └── tests.py
├── api/
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── templates/
│   ├── base.html
│   ├── register.html
│   ├── verify.html
│   └── card.html
├── media/                 # Outside the web root
├── static/
├── manage.py
├── requirements.txt
├── .env.example
└── README.md
```

### Key Patterns and Principles

- **Django built-ins first.** Auth, groups, permissions, sessions, admin, forms, validation, ORM, migrations, cache, email, and the test runner come from Django.
- **Proven packages second.** `django-auditlog`, `django-ratelimit`, `qrcode`, `cryptography`, and `django-environ` cover gaps Django does not fill. No custom reimplementation.
- **Admin as the back office.** Review queue, flags, renewal approval, user management, audit viewer, and CSV export are Django admin screens and actions.
- **Custom UI only where it matters.** Officer registration, public verification, and the ID card get templates. Everything else uses admin.
- **Computed status, never stored.** Licence colour is derived from `licence_expiry` and `now()`. Only manual states are stored.
- **Service layer for multi-step actions.** Approve, reject, flag, suspend, revoke, and renew are functions in `services.py`, wrapped in `transaction.atomic()`.
- **Least privilege.** Officers see the queue; supervisors see flags and approvals; super admins see everything; HR sees only their employer's nurses.
- **No unnecessary infrastructure.** No Docker, Redis, Celery, or separate search service for the demo.

### Status Model

Record status (stored): `pending`, `approved`, `rejected`, `flagged`, `suspended`, `revoked`.

Licence colour (computed):

| Colour | Rule |
|---|---|
| Green | More than 180 days to expiry |
| Yellow | 180 days or fewer |
| Red | Expired |
| Grey | Pending review |
| Black | Flagged, suspended, or revoked |

Thresholds are constants in `settings.py` for MVP. Database-configurable thresholds are post-demo.

### NANNM ID and QR

- Format: `PLT-NUR-` plus a zero-padded sequence, e.g. `PLT-NUR-000417`.
- Immutable after issue.
- QR encodes `PUBLIC_BASE_URL/verify/<nanm_id>`.
- QR image is generated on request, not stored.

---

## 7. Features

### 7.1 Officer Registration

- One form, officer-authenticated.
- Consent checkbox with `consent_at`; submission blocked without consent.
- Fields: full name, phone, email, NIN, licence number, licence expiry, specialty, cadre, employer, ward.
- Licence scan upload (PDF/JPG/PNG, max 10 MB) and selfie capture via browser camera with file fallback.
- Server-side validation with Django forms.
- Duplicate warning on NIN and licence number; duplicate still allowed but flagged in admin.
- Submitting creates a `pending` record linked to the officer.

**Assumption:** identity matching is manual. The officer compares selfie, licence photo, and NIN details. No NIN or biometric API in MVP.

### 7.2 Review Queue in Django Admin

- `NurseAdmin` list with filters: status, employer, licence colour, date.
- Read-only detail with inline licence documents and image previews.
- Admin actions: Approve, Reject with reason, Flag.
- Approve issues NANNM ID and sets `approved`.
- Reject requires a reason and notifies the nurse by email.
- Flag routes to the supervisor queue and sets black status.
- All actions write audit entries.

### 7.3 Public Verification

- Routes: `/verify` and `/verify/<nanm_id>`.
- Input: NANNM ID or QR scan.
- Output: name, photo, licence status, expiry, employer name, NANNM ID.
- Never output: NIN, licence number, phone, email, ward, address.
- Unknown ID returns "Not registered".
- Rate limited with `django-ratelimit`; honeypot field; no public listing endpoint.
- Revoked, suspended, flagged, and expired records show the corresponding state.

### 7.4 HR Portal

- HR users are in the `HR` group and linked to one employer via `Employer.hr_users`.
- HR logs into a read-only admin view scoped to their employer's nurses.
- Sees: name, photo, NANNM ID, licence status, expiry, ward, cadre, specialty, employer confirmation.
- Never sees: NIN, licence number, phone, email, audit log.
- HR can confirm employment through an admin action; `confirmed_at` and `confirmed_by` are stored.
- HR cannot edit nurse records.

### 7.5 Expiry and Reminders

- Daily management command `send_expiry_reminders`.
- Sends one email to nurses whose licence expires within `REMINDER_DAYS` (default 30) and who have not already been notified for that expiry date.
- Uses Django's `send_mail` with the SMTP backend.
- `Notification` rows prevent duplicate sends.
- Delivery failures are recorded and visible in admin.
- Run manually before the demo, or by cron on a VPS.

### 7.6 Renewal

- Officer opens a nurse in admin and adds a `LicenceDocument` of type `renewal` with the new expiry.
- Supervisor approves through an admin action.
- On approval: `licence_expiry` updates, status recomputes, old document remains in history.
- NANNM ID does not change.

### 7.7 ID Card and QR

- Printable HTML card with name, photo, NANNM ID, expiry, status, and QR.
- Print via the browser's print dialog; no PDF library.

**How a nurse gets the card:**
1. After approval, the officer lands on a confirmation page with two actions: **Print card** and **Copy card link**.
2. The officer prints the card on site during the ward drive, or saves it as PDF from the print dialog and sends it by email or WhatsApp.
3. The card link is a signed, expiring URL (Django signing, 7 days) that opens the same print-ready card. No nurse login is needed.
4. If the link expires, the nurse visits the NANNM office and an officer regenerates the card from admin.
5. The QR always resolves to the public verification page, so a printed or digital card stays verifiable.

- Card layout is credit-card sized with a print stylesheet; a plain A4 fallback is included.
- Cards are never downloadable from the public verification page.

### 7.8 Audit and Export

- `django-auditlog` registers Nurse, LicenceDocument, Employer, Flag, and User.
- Audit entries are viewed in Django admin.
- CSV export is a Django admin action available to super admins only.
- Every export writes an audit entry.

### 7.9 Seed Data

- `python manage.py seed_demo` creates:
  - 4 employers across LGAs.
  - 1 super admin, 2 officers, 1 supervisor, 2 HR users.
  - 60 nurses across green, yellow, red, pending, flagged, suspended, and revoked states.
  - Placeholder licence scans and selfies generated with Pillow.
  - A few renewal documents and notifications.
- The command is idempotent or refuses to run on a non-empty database unless `--reset` is passed.

---

## 8. Technology Stack

### Backend

| Component | Choice | Version | Why |
|---|---|---|---|
| Language | Python | 3.12+ | Team familiarity |
| Framework | Django | 5.x | Auth, admin, ORM, migrations, forms, email |
| API | Django REST Framework | 3.15+ | Thin versioned API for a future Vite frontend |
| API auth | DRF TokenAuthentication | Built into DRF | No extra JWT package |
| Database | SQLite (demo), PostgreSQL (deploy) | Built-in / 16 | Zero setup on laptops; Postgres when hosted |
| Templates | Jinja2 backend | Built into Django | Fast server-rendered pages |
| Admin | Django admin | Built into Django | Review queue, flags, users, audit, CSV |
| Audit | django-auditlog | 3.x | Proven package; no custom audit code |
| Rate limiting | django-ratelimit | 4.x | Public verification throttling |
| QR | qrcode + Pillow | Current | In-process QR; no external service |
| Encryption | cryptography (Fernet) | Current | NIN encryption at rest |
| Config | django-environ | Current | Environment variables without custom parsing |
| Static | WhiteNoise | Current | Static serving without nginx for the demo |
| Server | Gunicorn | Current | Optional VPS deployment |
| Email | Django built-in SMTP backend | Built into Django | No provider SDK or vendor lock-in |
| Tests | Django test runner | Built into Django | Smoke tests for core flows |
| Lint | ruff | Current | Optional local lint |

### Explicitly Not Used in MVP

- Docker (laptops run `runserver`; VPS can use Gunicorn directly)
- Celery and Redis (management commands cover scheduling)
- S3 and `django-storages` (local media is enough for the demo)
- WeasyPrint or xhtml2pdf (browser print covers the ID card)
- React or Next.js (Jinja templates cover the demo)
- Sentry (Django logging and `ADMINS` email are enough)

### Infrastructure

| Component | Choice |
|---|---|
| Demo | Laptop, `python manage.py runserver`, SQLite |
| Optional deployment | Single VPS or managed platform, Gunicorn + WhiteNoise, PostgreSQL |
| Email | Any SMTP server (Gmail/Workspace, Mailgun SMTP, SES SMTP, Postfix) |
| Media | Local folder outside the web root, permission-checked serving |
| Scheduler | Manual command before the demo; cron on a VPS |
| Backup | `sqlite3 .backup` or `pg_dump` plus a media archive, copied off the machine |
| TLS | Let's Encrypt or the platform's certificate on deployment |

### Dependency Policy

1. Use Django built-ins first.
2. Use a maintained package only where Django has no built-in.
3. Do not hand-roll audit, rate limiting, QR, encryption, or env parsing.
4. Do not add a service or daemon that the 4-day demo does not need.
5. Every new dependency must be justified in the pull request.

---

## 9. Security and Configuration

### Authentication and Authorization

- Django session auth for all logins.
- Groups: `Officer`, `Supervisor`, `Super Admin`, `HR`.
- Superuser for the system owner.
- HR scoping by `Employer.hr_users`; querysets filtered in admin.
- Officers can review; only supervisors and above can approve renewals, suspend, or revoke.
- Login throttling and lockout after repeated failures.
- CSRF protection, secure cookies, and clickjacking protection from Django defaults.
- `DEBUG=False` in any shared or deployed environment.

### Data Protection

- NDPA applies. NANNM Plateau Chapter is the proposed data controller; confirm in writing.
- NIN encrypted at rest with Fernet; key in an environment variable, never in the repo.
- NIN visible only to officers, supervisors, and super admins; masked elsewhere; never public or HR.
- Licence scans and selfies stored in `media/` outside the web root.
- Media served only through permission-checked Django views; no direct public URLs.
- Upload validation: content type, extension, size, and image/PDF parsing.
- Public verification rate-limited; no enumeration; honeypot.
- Audit log append-only; admin access restricted.
- Demo uses fake seeded data only. No real nurse PII in the demo database.
- Retention and deletion policy defined with NANNM before any real data is loaded.

### Configuration

Environment variables:

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Django secret |
| `DJANGO_DEBUG` | Debug flag; false outside local demo |
| `DATABASE_URL` | Optional PostgreSQL connection; SQLite if absent |
| `ALLOWED_HOSTS` | Host allowlist |
| `CSRF_TRUSTED_ORIGINS` | Trusted origins |
| `NIN_ENCRYPTION_KEY` | Fernet key for NIN |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | SMTP credentials |
| `EMAIL_USE_TLS` / `EMAIL_USE_SSL` | SMTP transport security |
| `DEFAULT_FROM_EMAIL` | Sender address |
| `SLACK_WEBHOOK_URL` | Optional admin alerts |
| `PUBLIC_BASE_URL` | QR and email links |
| `REMINDER_DAYS` | Days before expiry to send the reminder (default 30) |

Secrets live in the environment or a `.env` file that is never committed. `.env.example` documents required keys.

**Email note:** Django's built-in email backend sends through an SMTP server; it is not itself a mail server. Set `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` and point it at any SMTP account. For local testing, use the console backend.

### Security Scope

**In scope:** auth, groups, permissions, NIN encryption, permission-checked media, rate limiting, audit logging, CSRF, upload validation, secure cookies.

**Out of scope (MVP):** automated fraud detection, biometric liveness, NIN API verification, penetration testing, ISO 27001, DDoS protection beyond host defaults.

### Deployment Notes

- Laptop demo: SQLite, `runserver`, local media, console or real SMTP.
- VPS: Gunicorn + WhiteNoise, PostgreSQL, local media on a persistent volume, cron for reminders, TLS via nginx/Caddy or the platform.
- No provider-specific code. Only environment variables change.
- Back up the database and media before and after the demo.

---

## 10. API Specification

Base path: `/api/v1/`. JSON. Session auth for templates; DRF token auth for a future Vite frontend.

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/api/v1/auth/token/` | Public | Obtain DRF token |
| GET | `/api/v1/verify/{nanm_id}/` | Public, rate-limited | Minimal public result |
| GET | `/api/v1/nurses/` | Officer+ | List nurses |
| POST | `/api/v1/nurses/` | Officer | Register a nurse |
| GET | `/api/v1/nurses/{id}/` | Officer+ / HR (scoped) | Detail |
| POST | `/api/v1/nurses/{id}/approve/` | Officer | Approve and issue NANNM ID |
| POST | `/api/v1/nurses/{id}/licences/` | Officer | Upload initial or renewal licence |
| POST | `/api/v1/licences/{id}/approve/` | Supervisor+ | Approve a licence document |

**Public response example:**

```json
{
  "nanm_id": "PLT-NUR-000417",
  "full_name": "Adaeze Okafor",
  "photo_url": "/media/photo/placeholder.png",
  "licence_status": "licensed",
  "licence_expiry": "2028-03-14",
  "employer": "Plateau Specialist Hospital",
  "record_status": "approved"
}
```

**Not found:**

```json
{"detail": "Not registered"}
```

**Error format:**

```json
{
  "error": {
    "code": "validation_error",
    "message": "Licence expiry is required.",
    "fields": {"licence_expiry": ["This field is required."]}
  }
}
```

Status codes: `200`, `201`, `204`, `400`, `401`, `403`, `404`, `409`, `429`.

**Scope note:** the API is a compatibility layer. The demo UI and admin do not depend on it.

---

## 11. Success Criteria

### Demo Success Definition

A presenter can run `python manage.py migrate`, `python manage.py seed_demo`, and `python manage.py runserver`, then demonstrate the full flow in under 10 minutes on a laptop with no Docker and no cloud account.

### Functional Requirements

- [ ] Officer can register a nurse with consent, NIN, licence scan, and selfie
- [ ] Officer can approve, reject, and flag in Django admin
- [ ] Approval issues a unique NANNM ID
- [ ] QR resolves to the correct public page
- [ ] Officer can print the card or copy a signed card link after approval
- [ ] Public page shows only approved minimal fields
- [ ] HR sees only their employer's nurses and never NIN
- [ ] HR can confirm employment
- [ ] Status colours compute correctly
- [ ] One expiry reminder sends once per nurse per expiry date over SMTP
- [ ] Renewal updates expiry and recomputes status
- [ ] Suspend and revoke work and are audited
- [ ] Audit entries are visible in admin
- [ ] CSV export works and is audited
- [ ] Seed command produces 60 realistic records across all states

### Quality Indicators

- Public verification responds in under 1 second at p95 on seeded data.
- No NIN leakage in public, HR, logs, or email output.
- No unhandled 500s in the demo script.
- Core state transitions covered by smoke tests.
- Setup from a clean clone in under 15 minutes.

### User Experience Goals

- Officer completes one registration in under 3 minutes.
- Public verification takes under 15 seconds.
- Demo script runs end to end without manual database edits.
- Error messages name the field and the fix.

### Adoption Measure

Judges or the council can use the demo immediately after the event, and the same code can be deployed to a VPS or managed host without a rewrite.

---

## 12. Implementation Phases (4 Days)

### Day 1: Foundation and Registration

**Goal:** A running app with models, admin, seed data, and officer registration.

**Deliverables**
- [ ] Django project, settings, Jinja2 templates, `.env.example`
- [ ] Models: Nurse, LicenceDocument, Employer, Flag, Notification
- [ ] NIN encryption and masking
- [ ] Django admin for all models with basic list/filter/search
- [ ] Groups and permissions: Officer, Supervisor, Super Admin, HR
- [ ] `seed_demo` command with employers, users, and 60 nurses
- [ ] Officer registration form with consent, uploads, and selfie
- [ ] Smoke test for registration

**Validation:** An officer logs in, registers a nurse, and sees the pending record in admin.

### Day 2: Review, ID, and Public Verification

**Goal:** Approve a nurse and verify them publicly.

**Deliverables**
- [ ] Admin actions: Approve, Reject, Flag
- [ ] NANNM ID generation and state transitions
- [ ] QR generation endpoint
- [ ] Printable ID card template
- [ ] Approval confirmation page with Print card and Copy card link
- [ ] Signed, 7-day card link (Django signing), no nurse login
- [ ] Public verification page and API
- [ ] `django-ratelimit` on public verification
- [ ] Media serving through permission-checked views
- [ ] Smoke tests for approval and verification

**Validation:** Approve a seeded nurse, print the card, scan the QR, and see the correct public result.

### Day 3: HR, Renewal, Expiry, Audit, Export

**Goal:** The remaining selected flows, minimally implemented.

**Deliverables**
- [ ] HR group scoping by employer
- [ ] HR read-only admin view and employment confirmation action
- [ ] Renewal document upload and supervisor approval action
- [ ] Expiry status computation and colour filters
- [ ] `send_expiry_reminders` command with duplicate protection
- [ ] Real SMTP configuration and one email template
- [ ] `django-auditlog` registration and admin audit viewer
- [ ] CSV export admin action (super admin only)
- [ ] Suspension and revocation actions
- [ ] Smoke tests for HR scoping, renewal, and reminders

**Validation:** HR sees only their nurses; a renewal updates expiry; a reminder sends once; audit and CSV work.

### Day 4: Demo Polish and Handoff

**Goal:** A reliable, repeatable demo and a deployable app.

**Deliverables**
- [ ] Demo script with exact clicks and expected results
- [ ] Seed data polish: realistic names, employers, statuses, and placeholder images
- [ ] Empty-state and error-state review
- [ ] README with laptop setup, seed, run, and optional VPS deploy
- [ ] Backup and reset instructions
- [ ] Full smoke test pass
- [ ] Bug fixes only; no new features
- [ ] Optional: deploy to VPS or managed host if time allows

**Validation:** A second person follows the README and runs the demo from scratch without help.

**Timeline:** Four working days. Cut features from the bottom of Day 3 if time slips. Never cut registration, approval, or public verification.

---

## 13. Future Considerations

- Nurse self-registration and nurse login
- Offline-capable PWA for ward drives
- Vite frontend (React, Vue, or Svelte) on the existing API
- S3-compatible private storage with signed URLs
- SMS and WhatsApp reminders
- NMCN API integration or a formal data-sharing agreement
- Automated NIN and facial verification
- Printed ID cards
- Employment history and multi-employer records
- Database-configurable thresholds and reminder schedules
- Advanced dashboard and analytics
- Multi-state expansion
- Payments for renewals
- Bulk import of recovered paper records

---

## 14. Risks and Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | Four days is not enough for all selected flows | High | High | Django admin for back office; one reminder type; local media; SQLite; cut from the bottom of Day 3 first |
| 2 | Demo environment fails on the day | Medium | High | Laptop-first; no Docker; seed command; backup database and media; rehearse on the demo machine |
| 3 | Manual verification is slow at scale | High | Medium | Demo uses seeded data; real onboarding is phased by ward; bulk review is post-demo |
| 4 | Public lookup is scraped | Medium | Medium | Rate limit, honeypot, minimal output, no public list |
| 5 | SMTP deliverability fails during the demo | Medium | Medium | Test the SMTP account beforehand; keep a console-backend fallback; show the sent notification record |
| 6 | Local media is lost or exposed | Medium | High | Media outside web root, permission-checked serving, backup media folder, S3 post-demo |
| 7 | HR scoping bug exposes another employer's nurses | Low | High | Queryset scoping in one place, smoke test with two employers |
| 8 | NIN exposure creates NDPA risk | Medium | High | Encryption, masking, no NIN in public/HR/logs, fake demo data only |
| 9 | NANNM authority to enforce is unclear | High | High | Flag and notify only; manual suspend/revoke with reason; document the gap |
| 10 | Seeded demo data is mistaken for real records | Medium | Medium | Watermark or banner on demo data; README warning; fake names and placeholder images |
| 11 | Scope creep adds offline, mobile, or S3 | High | High | Out-of-scope list is explicit; no new features on Day 4 |
| 12 | Single laptop or single VPS loses data | Low | High | Export database and media before and after the event; store a copy off the machine |

---

## 15. Appendix

### 15.1 Data Model

**User** (Django built-in)
- `username`, `email`, `password`, `is_staff`, `is_superuser`, groups
- HR linked through `Employer.hr_users`

**Employer**
- `id`, `name`, `type`, `lga`, `contact_email`, `approved`, `hr_users` (M2M User)

**Nurse**
- `id`, `nanm_id` (unique, null until approval), `full_name`, `phone`, `email`
- `nin_encrypted`, `nin_last4`
- `photo`, `licence_number`, `licence_expiry`, `specialty`, `cadre`
- `employer` (FK), `ward`
- `record_status`, `consent_at`, `created_by` (FK User)
- `employer_confirmed_at`, `employer_confirmed_by`
- `created_at`, `updated_at`

**LicenceDocument**
- `id`, `nurse` (FK), `file`, `document_type` (`initial|renewal`)
- `uploaded_at`, `reviewed_by`, `decision` (`pending|approved|rejected`), `reason`, `reviewed_at`

**Flag**
- `id`, `nurse` (FK), `reason`, `raised_by`, `raised_at`, `resolved_by`, `resolved_at`, `resolution`

**Notification**
- `id`, `nurse` (FK), `type` (`expiry_reminder`), `sent_at`, `status`, `error`
- Unique constraint on (`nurse`, `type`, `licence_expiry`)

**Audit**
- `django-auditlog` LogEntry rows; no custom audit table

### 15.2 State Transitions

```
pending   -> approved | rejected | flagged
approved  -> suspended | revoked
suspended -> approved | revoked
flagged   -> approved | rejected | revoked
rejected  -> pending (on re-upload by an officer)
revoked   -> terminal
```

Every transition requires a reason except `pending -> approved`. Every transition is audited.

### 15.3 Data Exposure

| Field | Public | HR | Officer | Supervisor | Super Admin |
|---|---|---|---|---|---|
| Full name | Yes | Yes | Yes | Yes | Yes |
| Photo | Yes | Yes | Yes | Yes | Yes |
| NANNM ID | Yes | Yes | Yes | Yes | Yes |
| Licence status | Yes | Yes | Yes | Yes | Yes |
| Licence expiry | Yes | Yes | Yes | Yes | Yes |
| Employer name | Yes | Yes | Yes | Yes | Yes |
| Ward | No | Yes | Yes | Yes | Yes |
| Cadre / specialty | No | Yes | Yes | Yes | Yes |
| Licence number | No | No | Yes | Yes | Yes |
| NIN | No | No | Yes (masked, reveal audited) | Yes | Yes |
| Phone / email | No | No | Yes | Yes | Yes |
| Audit log | No | No | No | Limited | Yes |

### 15.4 Demo Script Outline

1. Run `seed_demo` and open the app.
2. Log in as an officer; register a new nurse.
3. Open admin; approve the record; show the NANNM ID.
4. Print the card from the confirmation page; copy the signed card link; scan the QR with a phone.
5. Show the public result; try an unknown ID.
6. Log in as HR; show scoped list and confirm employment.
7. Upload a renewal as an officer; approve as supervisor; show green status.
8. Run `send_expiry_reminders`; show the notification record and inbox.
9. Flag and revoke a fake record; show the public "Revoked" state.
10. Open the audit log; export CSV as super admin.

### 15.5 Assumptions

1. NANNM Plateau Chapter is the data controller; written confirmation is still required.
2. Identity verification is manual; no NIN or biometric API.
3. Licence validity is read from the uploaded expiry.
4. Nurses do not log in; officers handle registration, renewals, and card printing or sharing.
5. Demo data is fake; no real PII.
6. Internal admin uses Django admin.
7. One reminder type (expiry window) for MVP.
8. Local media for MVP; S3 is post-demo.
9. SQLite for the laptop demo; PostgreSQL for deployment.
10. Email uses Django's built-in SMTP backend.
11. No Docker, Redis, Celery, or S3 in the MVP.
12. The same code can run on a VPS or managed host by changing environment variables.

### 15.6 Open Items Before Real Data

- [ ] Written confirmation of NANNM Plateau Chapter as data controller
- [ ] Retention and deletion policy signed off
- [ ] Confirmation of NANNM's authority on expired, fake, or impersonated licences
- [ ] NMCN verification expectations confirmed
- [ ] Employer contact list and HR account approvals
- [ ] Production domain and SMTP sender domain
- [ ] Backup location and key custody
- [ ] Pilot ward and UAT schedule

### 15.7 Glossary

- **NANNM:** National Association of Nigerian Nurses and Midwives
- **NMCN:** Nursing and Midwifery Council of Nigeria
- **NDPA:** Nigeria Data Protection Act
- **NIN:** National Identification Number
- **LGA:** Local Government Area
- **Cadre:** Nursing grade or category (e.g., RN, RM, RN/RM)
- **QR:** Quick Response code
- **SMTP:** Simple Mail Transfer Protocol
