# Plan: Day 1 Core Registry (PNR-02 to PNR-10)

## Summary

Build the Day 1 foundation: registry models and migrations, NIN encryption, Django admin, role groups, protected media, officer registration with uploads and duplicate warnings, and repeatable demo seed data. This plan covers PNR-02 through PNR-10 as one dependency-ordered implementation because the stories share models, permissions, and registration flow.

## User Story

As a NANNM field officer and system owner
I want a secure registry data layer and a working officer registration flow
So that nurses can be registered, reviewed, and demoed without manual setup

## Metadata

| Field | Value |
|-------|-------|
| Type | NEW_CAPABILITY |
| Complexity | HIGH |
| Systems Affected | `registry/` models, migrations, admin, forms, views, permissions, crypto, management commands, templates, settings |
| GitHub Issues | #3–#11 (PNR-02–PNR-10) |

---

## Patterns to Follow

### App and URL structure

```python
# SOURCE: registry/apps.py:4-6
class RegistryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "registry"
```

```python
# SOURCE: registry/urls.py:5-9
app_name = "registry"

urlpatterns = [
    path("", views.home, name="home"),
]
```

### Thin views

```python
# SOURCE: registry/views.py:4-5
def home(request):
    return render(request, "home.html")
```

### Configuration

```python
# SOURCE: config/settings.py:7-16
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    REMINDER_DAYS=(int, 30),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-local-demo-only")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
```

```python
# SOURCE: config/settings.py:103-112
DATABASE_URL = env("DATABASE_URL", default="")
if DATABASE_URL:
    DATABASES = {"default": env.db_url("DATABASE_URL")}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
```

### Tests

```python
# SOURCE: registry/tests.py:5-14
class HomePageTests(TestCase):
    def test_home_page_renders(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Plateau State Nurse Registry")
        self.assertContains(response, "Registration and licence verification")

    def test_debug_defaults_to_false(self):
        self.assertFalse(settings.DEBUG)
```

No models, forms, or admin classes exist yet. Establish those patterns in this plan.

---

## Files to Change

| File | Action | Purpose |
|------|--------|---------|
| `registry/models.py` | CREATE | `Employer`, `Nurse`, `LicenceDocument`, `Flag`, `Notification` |
| `registry/migrations/0001_initial.py` | CREATE | Initial schema |
| `registry/migrations/0002_nin_hash.py` | CREATE | Duplicate-detection blind index |
| `registry/crypto.py` | CREATE | Fernet encryption, decryption, NIN hashing |
| `registry/permissions.py` | CREATE | Group names, role checks, HR scoping |
| `registry/services.py` | CREATE | `reveal_nin`, shared status helpers |
| `registry/admin.py` | CREATE | Registry admin, filters, previews, duplicate markers |
| `registry/forms.py` | CREATE | Registration form, upload validation, duplicate warnings |
| `registry/views.py` | UPDATE | Registration, confirmation, protected media |
| `registry/urls.py` | UPDATE | Registration and protected media routes |
| `registry/tests.py` | UPDATE | Model, crypto, permissions, admin, media, registration, seed tests |
| `registry/management/__init__.py` | CREATE | Management package |
| `registry/management/commands/__init__.py` | CREATE | Commands package |
| `registry/management/commands/setup_groups.py` | CREATE | Idempotent group/permission setup |
| `registry/management/commands/seed_demo.py` | CREATE | Repeatable demo data |
| `config/jinja2.py` | CREATE | Expose `url` and `static` to Jinja2 |
| `config/settings.py` | UPDATE | Media, NIN key, auditlog, Jinja2 environment |
| `requirements.txt` | UPDATE | Pillow, cryptography, django-auditlog |
| `templates/base.html` | UPDATE | Registration and admin links |
| `templates/register.html` | CREATE | Officer registration form |
| `templates/registration_success.html` | CREATE | Pending confirmation page |
| `README.md` | UPDATE | `setup_groups` and `seed_demo` commands |

---

## Tasks

Execute in this order. It differs from numeric story order to keep dependencies and security boundaries intact.

### Task 1: PNR-02 — Core models and migrations

- **Files**: `registry/models.py`, `registry/migrations/0001_initial.py`, `requirements.txt`
- **Action**: CREATE / UPDATE
- **Implement**:
  - Add `Pillow` to `requirements.txt`; `ImageField` needs it at check time.
  - `Employer`: `name`, `type` (`TextChoices`: hospital, primary health centre, clinic, other), `lga`, `contact_email`, `approved`, `hr_users` M2M to `settings.AUTH_USER_MODEL` (`blank=True`, `related_name="employers"`), `created_at`.
  - `Nurse`: `nanm_id` (`unique=True`, `null=True`, `blank=True`), `full_name`, `phone`, `email`, `nin_encrypted` (`TextField`, blank), `nin_last4` (`CharField(max_length=4)`, blank), `photo` (`ImageField(upload_to="nurse_photos/")`, blank), `licence_number`, `licence_expiry`, `specialty`, `cadre`, `employer` (`FK`, `PROTECT`, `related_name="nurses"`), `ward`, `record_status` (`TextChoices`: pending, approved, rejected, flagged, suspended, revoked; default pending), `consent_at`, `created_by` (`FK`, `PROTECT`, `related_name="created_nurses"`), `employer_confirmed_at`, `employer_confirmed_by` (`FK`, `SET_NULL`), `created_at`, `updated_at`.
  - `LicenceDocument`: `nurse` (`FK`, `CASCADE`, `related_name="documents"`), `file` (`FileField(upload_to="licence_scans/%Y/%m/")`), `document_type` (`TextChoices`: initial, renewal), `uploaded_at`, `reviewed_by` (`FK`, `SET_NULL`), `decision` (`TextChoices`: pending, approved, rejected), `reason`, `reviewed_at`.
  - `Flag`: `nurse` (`FK`, `CASCADE`, `related_name="flags"`), `reason`, `raised_by` (`FK`, `PROTECT`), `raised_at`, `resolved_by` (`FK`, `SET_NULL`), `resolved_at`, `resolution`.
  - `Notification`: `nurse` (`FK`, `CASCADE`, `related_name="notifications"`), `type` (`TextChoices`: expiry_reminder), `licence_expiry` (`DateField`), `sent_at`, `status` (`TextChoices`: pending, sent, failed), `error`.
  - Add `Meta.indexes` on `Nurse.licence_expiry` and `Nurse.record_status`; `nanm_id` unique index is implicit; FK indexes are implicit.
  - Add `CheckConstraint` for `record_status` allowed values.
  - Add `CheckConstraint` `approved_requires_nanm_id`: an approved nurse must have `nanm_id`.
  - Add `UniqueConstraint` on `Notification(nurse, type, licence_expiry)`.
  - Add `__str__` methods.
  - Generate and commit migrations.
- **Mirror**: `config/settings.py:103-112` for settings style; `registry/apps.py:4-6` for app conventions.
- **Validate**: `python manage.py makemigrations registry`, `python manage.py migrate`, `python manage.py makemigrations --check --dry-run`.

### Task 2: PNR-05 — Roles, groups, and HR scoping

- **Files**: `registry/permissions.py`, `registry/management/commands/setup_groups.py`, `registry/tests.py`
- **Action**: CREATE / UPDATE
- **Implement**:
  - Constants: `OFFICER`, `SUPERVISOR`, `SUPER_ADMIN`, `HR`.
  - Helpers: `is_officer`, `is_supervisor`, `is_super_admin`, `is_hr`, `is_officer_or_above`, `can_approve_renewal`, `can_suspend_or_revoke`, `nurses_for_user`.
  - `nurses_for_user`: HR sees `Nurse.objects.filter(employer__hr_users=user)`; officer/supervisor/super admin see all; no group sees none.
  - `setup_groups` command: idempotent `get_or_create` for the four groups; assign model permissions by codename. Officer: view/change nurse. Supervisor: officer perms plus view/change flag and licence document. Super Admin: all registry permissions. HR: view nurse and view employer only.
  - Do not create a custom role model.
- **Mirror**: `registry/tests.py:5-14` for test structure.
- **Validate**: `python manage.py setup_groups`, `python manage.py test registry`.

### Task 3: PNR-06 — Protected media

- **Files**: `config/settings.py`, `registry/views.py`, `registry/urls.py`, `registry/tests.py`
- **Action**: UPDATE
- **Implement**:
  - Add `MEDIA_URL = "/media/"`, `MEDIA_ROOT = BASE_DIR / "media"`.
  - Add `protected_document(request, pk)` and `protected_nurse_photo(request, pk)`.
  - Use `FileResponse`; never expose `MEDIA_URL` directly.
  - Resolve `Path(file.path)` and reject anything outside `MEDIA_ROOT` with `Http404`.
  - Authorization: officer/supervisor/super admin can view documents; HR can view photos only for nurses at their employer; public cannot view either.
  - Add routes `documents/<int:pk>/` and `nurses/<int:pk>/photo/`.
  - Do not add a `MEDIA_URL` URL pattern.
- **Mirror**: `registry/views.py:4-5` thin view; `registry/urls.py:5-9` route style.
- **Validate**: `python manage.py test registry`.

### Task 4: PNR-03 — NIN encryption, masking, and audited reveal

- **Files**: `registry/crypto.py`, `registry/services.py`, `registry/models.py`, `config/settings.py`, `requirements.txt`, `registry/tests.py`
- **Action**: CREATE / UPDATE
- **Implement**:
  - Add `cryptography` and `django-auditlog` to `requirements.txt`.
  - Add `auditlog` to `INSTALLED_APPS` and `auditlog.middleware.AuditlogMiddleware`.
  - Add `NIN_ENCRYPTION_KEY = env("NIN_ENCRYPTION_KEY", default="")` to settings.
  - `crypto.py`: `get_fernet()` raises `ImproperlyConfigured` with a clear message when the key is missing or invalid; `encrypt_nin`, `decrypt_nin`, `hash_nin` (HMAC-SHA256 using a key derived from `NIN_ENCRYPTION_KEY`), `mask_nin`.
  - `Nurse.set_nin(raw)` sets `nin_encrypted` and `nin_last4`; `Nurse.get_nin()` decrypts; `Nurse.nin_masked` returns `*******{last4}`.
  - `services.reveal_nin(actor, nurse)`: allow Officer, Supervisor, Super Admin; deny HR and anonymous; write an `auditlog.Action.ACCESS` entry; return plaintext only to the caller.
  - Never add a plaintext NIN field.
- **Mirror**: `config/settings.py:7-16` env style; `registry/tests.py:5-14` test style.
- **Validate**: `python manage.py test registry`.

### Task 5: PNR-04 — Django admin back office

- **Files**: `registry/admin.py`, `registry/tests.py`
- **Action**: CREATE / UPDATE
- **Implement**:
  - Register `Employer`, `Nurse`, `LicenceDocument`, `Flag`, `Notification`.
  - `NurseAdmin`: `list_display` (NANNM ID, name, status, expiry, employer), `list_filter` (status, employer, expiry date), `search_fields` (name, NANNM ID, licence number, phone), `readonly_fields` (`nanm_id`, `created_at`, `updated_at`, `consent_at`, `created_by`, `employer_confirmed_at`, `employer_confirmed_by`), `date_hierarchy = "licence_expiry"`.
  - Inline `LicenceDocument` and `Flag` on nurse detail.
  - `LicenceDocumentAdmin`: link preview through the protected media view, not `file.url`.
  - `EmployerAdmin`: search and filter by LGA and approved.
  - No custom dashboard, theme, or templates.
- **Mirror**: `registry/urls.py:5-9` naming; `config/urls.py:4-7` admin route.
- **Validate**: `python manage.py test registry`; log in as superuser and open admin.

### Task 6: PNR-07 — Officer registration and consent

- **Files**: `config/jinja2.py`, `config/settings.py`, `registry/forms.py`, `registry/views.py`, `registry/urls.py`, `templates/register.html`, `templates/registration_success.html`, `templates/base.html`, `registry/models.py`, `registry/tests.py`
- **Action**: CREATE / UPDATE
- **Implement**:
  - Add `config/jinja2.py` environment exposing `url` and `static`; set `OPTIONS["environment"] = "config.jinja2.environment"` for the Jinja2 backend.
  - `NurseRegistrationForm(ModelForm)`: fields full name, phone, email, NIN (custom `CharField`), licence number, licence expiry, specialty, cadre, employer, ward, consent checkbox.
  - Validate phone (`^\+?[0-9]{10,15}$`), NIN (`^\d{11}$`), email, and consent.
  - `save(commit=False)`: set `created_by`, `record_status=pending`, `consent_at=timezone.now()`, call `set_nin`.
  - `Nurse.reference` property: `REQ-{pk:06d}`.
  - `register` view: `@login_required`, officer-or-above only, redirect anonymous to login, 403 for no group.
  - `registration_success` view: show reference and pending status.
  - Routes `register/` and `register/success/<int:pk>/`.
  - Mobile-first, one-column templates; add registration link to `base.html`.
- **Mirror**: `registry/views.py:4-5` thin view; `registry/urls.py:5-9` route style; `templates/home.html:1-8` template style.
- **Validate**: `python manage.py test registry`; open `/register/` anonymously and as officer.

### Task 7: PNR-08 — Licence scan and selfie upload

- **Files**: `registry/forms.py`, `registry/views.py`, `templates/register.html`, `registry/tests.py`
- **Action**: UPDATE
- **Implement**:
  - Add `licence_scan` (`FileField`) and `selfie` (`ImageField`) to the registration form.
  - Validate extension (`.pdf`, `.jpg`, `.jpeg`, `.png`), content type, and size ≤10 MB.
  - Parse images with Pillow; for PDFs check the `%PDF` header.
  - Save in `transaction.atomic()`: `nurse.photo = selfie`; create `LicenceDocument(nurse=nurse, file=scan, document_type=initial)`.
  - Template: `enctype="multipart/form-data"`; file inputs; camera capture via `getUserMedia` with a file-input fallback.
  - Render stored files through protected media routes only.
- **Mirror**: `registry/forms.py` from Task 6; `registry/views.py:4-5`.
- **Validate**: `python manage.py test registry`; upload valid PDF/JPG/PNG and an over-size file.

### Task 8: PNR-09 — Duplicate detection warning

- **Files**: `registry/models.py`, `registry/crypto.py`, `registry/forms.py`, `registry/admin.py`, `registry/migrations/0002_nin_hash.py`, `registry/tests.py`
- **Action**: UPDATE / CREATE
- **Implement**:
  - Add `nin_hash` (`CharField(max_length=64)`, `db_index=True`, blank) to `Nurse`.
  - `set_nin` also sets `nin_hash = hash_nin(raw)`.
  - Form `clean`: query `Nurse.objects.filter(nin_hash=...)` and `licence_number__iexact=...`, excluding the current instance.
  - If duplicates exist, set `duplicate_warning` and require `confirm_duplicate`; without confirmation, add a form error. With confirmation, allow save.
  - Do not add a hard unique constraint on NIN or licence number.
  - Admin: annotate duplicate counts in `get_queryset` and show a `possible_duplicate` column.
- **Mirror**: `registry/tests.py:5-14`.
- **Validate**: `python manage.py makemigrations registry`, `python manage.py migrate`, `python manage.py test registry`.

### Task 9: PNR-10 — Seed demo data

- **Files**: `registry/management/commands/seed_demo.py`, `registry/tests.py`
- **Action**: CREATE / UPDATE
- **Implement**:
  - `seed_demo` calls `setup_groups`.
  - Create 4 employers, 1 super admin, 2 officers, 1 supervisor, 2 HR users.
  - Create 60 nurses: 30 green, 10 yellow, 5 red, 5 pending, 5 flagged, 3 suspended, 2 revoked.
  - Approved nurses get sequential `PLT-NUR-000001` IDs.
  - Use fixed fake names, NINs, licence numbers, phone numbers, and emails. No Faker.
  - Generate placeholder selfie and licence JPEGs with Pillow under `MEDIA_ROOT`.
  - Add a few renewal documents and notifications.
  - Refuse to run on a non-empty database unless `--reset`; `--reset` deletes only seeded demo data and demo users.
  - Print login credentials and a summary.
- **Mirror**: `registry/management/commands/setup_groups.py` from Task 2.
- **Validate**: `python manage.py seed_demo`, `python manage.py seed_demo` again (must refuse), `python manage.py seed_demo --reset`.

---

## Validation

```bash
source .venv/bin/activate
pip install -r requirements.txt

python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py migrate
python manage.py setup_groups
python manage.py seed_demo
python manage.py runserver 127.0.0.1:8000
```

### End-to-end checks

- [ ] `seed_demo` on an empty database creates the expected counts and prints credentials.
- [ ] A second `seed_demo` without `--reset` refuses with a clear message.
- [ ] Anonymous `/register/` redirects to login.
- [ ] Officer login can open `/register/` and submit a valid nurse.
- [ ] Submission creates a `pending` nurse linked to the officer with `consent_at` set.
- [ ] Confirmation page shows `REQ-000001` and pending status.
- [ ] Missing consent blocks submission with a clear error.
- [ ] Uploading a valid PDF/JPG/PNG creates a `LicenceDocument` and nurse photo.
- [ ] Uploading an over-size or unsupported file shows a field error.
- [ ] A duplicate NIN or licence number shows a warning; confirmation allows submission.
- [ ] Officer can open a protected document URL; anonymous and HR cannot.
- [ ] Direct `/media/...` requests return 404.
- [ ] Superuser sees all registry models in admin; non-staff is denied.
- [ ] NIN is ciphertext in the database and round-trips through `set_nin`/`get_nin`.
- [ ] `reveal_nin` works for officers and writes an audit entry.
- [ ] HR queryset returns only their employer's nurses.

---

## Acceptance Criteria

### PNR-02

- [ ] Fresh migrations create `Employer`, `Nurse`, `LicenceDocument`, `Flag`, `Notification`.
- [ ] Approved nurses require a unique, non-null `nanm_id`.
- [ ] Duplicate `Notification(nurse, type, licence_expiry)` is rejected.
- [ ] Invalid `record_status` is rejected.
- [ ] No pending migrations remain.

### PNR-03

- [ ] NIN is stored as ciphertext, never plaintext.
- [ ] Authorized reveal returns the NIN and writes an audit entry.
- [ ] HR/public views expose only `nin_last4`.
- [ ] Missing or invalid `NIN_ENCRYPTION_KEY` raises a clear configuration error.
- [ ] Encryption/decryption round-trip tests pass.

### PNR-04

- [ ] Superuser sees all registry models in admin.
- [ ] Nurse list filters by status, employer, and expiry window.
- [ ] `nanm_id`, timestamps, and audit fields are read-only.
- [ ] Licence document preview is visible through the protected view.
- [ ] Non-staff users are denied.

### PNR-05

- [ ] Four groups exist with intended permissions after `setup_groups`.
- [ ] Officer cannot revoke an ID.
- [ ] Supervisor can approve a renewal.
- [ ] HR sees only their employer's nurses.
- [ ] Users in no group are denied staff access.

### PNR-06

- [ ] Uploads land under `media/`, not `static/`.
- [ ] Unauthorized direct media access is denied.
- [ ] Authorized officers can fetch documents.
- [ ] Path traversal is rejected.
- [ ] Public verification exposes no private document URL.

### PNR-07

- [ ] Anonymous registration access redirects to login.
- [ ] Valid officer submission creates a `pending` nurse linked to the officer.
- [ ] Missing consent is rejected with a clear error.
- [ ] `consent_at` is set on success.
- [ ] Confirmation shows reference and pending status.

### PNR-08

- [ ] PDF/JPG/PNG under 10 MB is accepted and linked.
- [ ] Over-size or unsupported files show field errors.
- [ ] Camera capture attaches an image; file fallback works.
- [ ] Stored documents render through protected media.

### PNR-09

- [ ] Existing NIN shows a duplicate warning.
- [ ] Existing licence number shows a duplicate warning.
- [ ] Confirmation still allows submission.
- [ ] Admin visibly marks possible duplicates.
- [ ] No duplicate means no warning.

### PNR-10

- [ ] Empty database seed creates 4 employers, 6 staff/HR users, and 60 nurses.
- [ ] Seed covers green, yellow, red, pending, flagged, suspended, and revoked.
- [ ] Placeholder scans and selfies render.
- [ ] Non-empty database refuses without `--reset`.
- [ ] Successful seed prints credentials and summary.

---

## Risks

| Risk | Mitigation |
|------|------------|
| Fernet is non-deterministic, so NIN cannot be queried by ciphertext | Add `nin_hash` HMAC blind index in PNR-09; never store plaintext. |
| Django admin requires `DjangoTemplates` alongside Jinja2 | Keep both backends; Jinja2 first for app pages. |
| Jinja2 has no `url` global by default | Add `config/jinja2.py` and set it in `TEMPLATES`. |
| `ImageField` requires Pillow at system-check time | Add Pillow in PNR-02, before models. |
| Audit reveal needs `django-auditlog` before PNR-23 | Add the dependency in PNR-03; PNR-23 expands registration and viewer. |
| `approved_requires_nanm_id` blocks premature approval | PNR-11/12 must issue the NANNM ID before setting `approved`. |
| Upload validation can be bypassed by crafted content types | Check extension, content type, size, Pillow parsing, and PDF header. |
| Protected media path traversal | Resolve paths and enforce `is_relative_to(MEDIA_ROOT)`; prefer ID-based routes. |
| `seed_demo --reset` is destructive | Require explicit `--reset`; delete only known demo users and registry data. |
| PNR-03 startup key check breaks clean-clone checks | Validate in `get_fernet()` with a clear error; document key generation in `.env.example`. |

---

## Deviations / Notes

- This is one combined Day 1 plan covering PNR-02–PNR-10; implement tasks in the order above, not numeric order.
- PNR-03 adds `django-auditlog` early so NIN reveal is audited; PNR-23 remains the admin audit viewer story.
- PNR-09 adds `nin_hash`, which is not in the PRD data model, to support duplicate detection without storing plaintext.
- PNR-03 validates the encryption key when crypto is used rather than at process import, so `manage.py check` remains usable without a key.
