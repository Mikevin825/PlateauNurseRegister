# Plan: Day 2 Review, ID Card, and Public Verification

## Summary

Build the Day 2 workflow on top of the existing registration foundation: officers approve, reject, or flag pending nurses from Django admin; approval issues an immutable NANNM ID; officers get a print-ready ID card and a signed 7-day card link; the public verifies a nurse by NANNM ID or QR through the same minimal payload used by the API. Business rules stay in `registry/services.py`, public and card views stay thin, and `django-ratelimit` protects the public lookup.

## User Story

As an officer, supervisor, and member of the public
I want to review registrations, issue IDs, print cards, and verify nurses
So that only verified nurses appear publicly and anyone can confirm registration and licence status quickly.

## Metadata

| Field | Value |
|-------|-------|
| Type | NEW_CAPABILITY |
| Complexity | MEDIUM |
| Systems Affected | `registry`, `api`, `config`, `templates`, `static`, `requirements.txt`, docs |
| GitHub Issues | `#12` PNR-11, `#13` PNR-12, `#14` PNR-13, `#15` PNR-14, `#16` PNR-15, `#17` PNR-16 |
| Jira Issue | N/A; GitHub issues are the tracker |

---

## Patterns to Follow

### Naming and service boundaries

```python
# SOURCE: registry/services.py:1-19
from django.core.exceptions import PermissionDenied

from .permissions import can_reveal_nin


def reveal_nin(actor, nurse):
    if not can_reveal_nin(actor):
        raise PermissionDenied("You do not have permission to reveal this NIN.")

    from auditlog import get_logentry_model

    LogEntry = get_logentry_model()
    LogEntry.objects.log_create(
        nurse,
        action=LogEntry.Action.ACCESS,
        actor=actor,
        force_log=True,
    )
    return nurse.get_nin()
```

Use the same shape for transitions: permission check, atomic service function, audit write, return the updated record. Views and admin actions call services; they do not mutate `record_status` directly.

### Thin protected views

```python
# SOURCE: registry/views.py:55-73
@login_required
def protected_document(request, pk):
    if not can_view_documents(request.user):
        raise PermissionDenied

    document = get_object_or_404(
        LicenceDocument.objects.select_related("nurse__employer"),
        pk=pk,
    )
    return _serve_media(document.file)


@login_required
def protected_nurse_photo(request, pk):
    nurse = get_object_or_404(Nurse.objects.select_related("employer"), pk=pk)
    if not can_view_nurse_photo(request.user, nurse):
        raise PermissionDenied

    return _serve_media(nurse.photo)
```

Public card/verification views must be explicitly public only where the PRD allows it. Reuse `_serve_media` for the public photo route; never expose `MEDIA_URL` directly.

### Admin read-only status and existing fields

```python
# SOURCE: registry/admin.py:40-64
@admin.register(Nurse)
class NurseAdmin(admin.ModelAdmin):
    list_display = (
        "nanm_id",
        "full_name",
        "record_status",
        "licence_expiry",
        "employer",
        "possible_duplicate",
    )
    list_filter = ("record_status", "employer", "licence_expiry")
    search_fields = ("nanm_id", "full_name", "licence_number", "phone")
    date_hierarchy = "licence_expiry"
    readonly_fields = (
        "nanm_id",
        "nin_last4",
        "record_status",
        "created_at",
        "updated_at",
        "consent_at",
        "created_by",
        "employer_confirmed_at",
        "employer_confirmed_by",
    )
    inlines = (LicenceDocumentInline, FlagInline)
```

Keep `record_status` and `nanm_id` read-only. Add admin actions; do not add editable status fields.

### Model constraints and ID field

```python
# SOURCE: registry/models.py:40, 54-58, 98-104
nanm_id = models.CharField(max_length=32, unique=True, null=True, blank=True)
record_status = models.CharField(
    max_length=16,
    choices=RecordStatus.choices,
    default=RecordStatus.PENDING,
)
models.CheckConstraint(
    condition=(
        models.Q(record_status="approved", nanm_id__isnull=False)
        | ~models.Q(record_status="approved")
    ),
    name="approved_nurse_requires_nanm_id",
),
```

The database already enforces that an approved nurse has an ID. Issue the ID before saving `approved`; do not add a migration for existing fields.

### URL naming

```python
# SOURCE: registry/urls.py:1-21
app_name = "registry"

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path(
        "register/success/<int:pk>/",
        views.registration_success,
        name="registration_success",
    ),
    path("documents/<int:pk>/", views.protected_document, name="protected_document"),
    path(
        "nurses/<int:pk>/photo/",
        views.protected_nurse_photo,
        name="protected_nurse_photo",
    ),
]
```

Use `snake_case` names and `registry:` namespaces. Add all new routes to `registry/urls.py`; add the API namespace in `config/urls.py`.

### Tests

```python
# SOURCE: registry/tests.py:115-131
def create_nurse(self, **kwargs):
    values = {
        "full_name": "Test Nurse",
        "phone": "08030000001",
        "email": "nurse@example.test",
        "licence_number": f"LIC-{Nurse.objects.count() + 1}",
        "licence_expiry": timezone.localdate() + timedelta(days=365),
        "employer": self.employer,
        "record_status": Nurse.RecordStatus.PENDING,
    }
    nin = kwargs.pop("nin", None)
    values.update(kwargs)
    nurse = Nurse(**values)
    if nin:
        nurse.set_nin(nin)
    nurse.save()
    return nurse
```

Use `RegistryTestBase`, `self.create_nurse(...)`, `reverse("registry:...")`, and `override_settings`. Keep tests independent of network, SMTP, and real PII. Use Django's locmem email backend automatically provided by the test runner.

### Jinja2 templates

```html
<!-- SOURCE: templates/base.html:1-20 -->
<title>{% block title %}Plateau State Nurse Registry{% endblock %}</title>
...
<a href="{{ url('registry:register') }}">Register nurse</a>
...
{% block content %}{% endblock %}
```

Call methods explicitly in Jinja: `{{ form.as_p() }}`, `{{ form.non_field_errors() }}`, `{{ nurse.get_record_status_display() }}`. Add `{% block extra_head %}{% endblock %}` to `base.html` for card CSS.

---

## Design Decisions

- Stored statuses remain exactly `pending`, `approved`, `rejected`, `flagged`, `suspended`, `revoked`.
- Allowed transitions live in one map in `registry/services.py`:

```text
pending   -> approved | rejected | flagged
approved  -> suspended | revoked
suspended -> approved | revoked
flagged   -> approved | rejected | revoked
rejected  -> pending
revoked   -> terminal
```

- Every transition except `pending -> approved` requires a non-empty reason. Day 2 uses only approve, reject, and flag; the map can include later transitions without adding Day 3 actions yet.
- `approved` status and `nanm_id` are set in the same transaction. Existing `approved` records keep their ID on re-approval.
- NANNM ID format is `PLT-NUR-` plus a six-digit zero-padded sequence, e.g. `PLT-NUR-000417`. Generate from the maximum existing suffix inside a transaction and retry once on `IntegrityError`.
- `Nurse.save()` rejects changes to an already-issued `nanm_id` with `ValidationError`. Admin already marks it read-only; the model guard covers code paths.
- QR content is `f"{settings.PUBLIC_BASE_URL.rstrip('/')}/verify/{nanm_id}/"`. Generate PNG bytes on request; never save a QR file.
- Public status labels are `Licensed`, `Expiring soon`, `Expired`, `Pending`, `Flagged`, `Suspended`, `Revoked`. Use `settings.LICENCE_EXPIRY_WARNING_DAYS` default `180`. Day 3 `PNR-20` extends this into colours and admin filters.
- Public verification and API share `api.serializers.PublicNurseSerializer` and expose only `nanm_id`, `full_name`, `photo_url`, `licence_status`, `licence_expiry`, `employer`, and `record_status`. Never expose NIN, licence number, phone, email, ward, address, or audit data.
- Unknown IDs return “Not registered” on the web page and `{"detail": "Not registered"}` with HTTP 404 from the API.
- Public photo route is `/verify/<nanm_id>/photo/` and serves only through `_serve_media`. It is reachable only by exact NANNM ID, not by enumeration.
- Card access:
  - `/nurses/<pk>/card/` requires login and officer-or-above.
  - `/card/<token>/` requires no login but needs a valid signed token with `max_age=settings.CARD_LINK_MAX_AGE` (7 days).
  - Invalid or expired tokens render `card_invalid.html` with HTTP 400.
- Approval confirmation is `/nurses/<pk>/approval/`, requires login and officer-or-above, and shows **Print card**, **Copy card link**, and **Email card link**. Only approved nurses with an ID can reach it.
- Rejection email uses `django.core.mail.send_mail` and `templates/email/registration_rejected.txt`. Tests use locmem. Email failure must not roll back the rejection; catch and log the failure. Full SMTP configuration remains Day 3 `PNR-22`.
- Rate limiting uses `django-ratelimit` on the public verification form, result page, photo, QR, and API. Default `PUBLIC_VERIFY_RATE=30/m`; document it in `.env.example`. Tests disable it except the dedicated 429 test.
- Honeypot field name is `website`. If filled, return HTTP 400 without a lookup.
- No public list, search-by-name, or bulk endpoint.

---

## Files to Change

| File | Action | Purpose |
|------|--------|---------|
| `requirements.txt` | UPDATE | Add `djangorestframework`, `qrcode`, `django-ratelimit` pins |
| `.env.example` | UPDATE | Document public verification, card, and email settings |
| `config/settings.py` | UPDATE | Add DRF, `api`, rate-limit middleware/cache, card/public settings |
| `config/urls.py` | UPDATE | Include `/api/v1/` |
| `registry/models.py` | UPDATE | Enforce immutable `nanm_id` on save |
| `registry/services.py` | UPDATE | Add transition map, ID issuance, approve/reject/flag, public status |
| `registry/forms.py` | UPDATE | Add admin reason form |
| `registry/admin.py` | UPDATE | Add approve/reject/flag actions and confirmation flow |
| `registry/views.py` | UPDATE | Add verification, QR, public photo, card, signed link, approval confirmation, email link, 429 handler |
| `registry/urls.py` | UPDATE | Add Day 2 routes |
| `templates/base.html` | UPDATE | Add verification nav link and `extra_head` block |
| `templates/verify.html` | CREATE | Public verification form and result |
| `templates/card.html` | CREATE | Print-ready ID card |
| `templates/card_invalid.html` | CREATE | Clear invalid/expired link error |
| `templates/approval_confirmation.html` | CREATE | Post-approval print/copy/email page |
| `templates/admin_review_confirm.html` | CREATE | Jinja admin-action confirmation page |
| `templates/email/registration_rejected.txt` | CREATE | Rejection email body |
| `static/css/card.css` | CREATE | Credit-card print styles and A4 fallback |
| `api/__init__.py` | CREATE | API package |
| `api/apps.py` | CREATE | API app config |
| `api/serializers.py` | CREATE | Shared public nurse serializer |
| `api/views.py` | CREATE | Public verify endpoint |
| `api/urls.py` | CREATE | `/api/v1/verify/<nanm_id>/` |
| `api/tests.py` | CREATE | API payload, 404, rate limit tests |
| `registry/tests.py` | UPDATE | Transition, ID, card, verification, admin, rate-limit tests |
| `README.md` | UPDATE | Document Day 2 routes, settings, and smoke path |

No schema migration is expected. If `makemigrations --check --dry-run` reports one, stop and investigate before committing.

---

## Tasks

Execute in order. Each task is atomic and verifiable.

### Task 1: Add dependencies and public/card settings

- **File**: `requirements.txt`, `.env.example`, `config/settings.py`
- **Action**: UPDATE
- **Implement**:
  - Add `djangorestframework>=3.15,<4`, `qrcode>=8,<9`, `django-ratelimit>=4,<5`.
  - Add `rest_framework` to `INSTALLED_APPS`; add `api` in Task 6 when the package exists.
  - Add `django_ratelimit.middleware.RatelimitMiddleware` after authentication/messages middleware.
  - Add `CACHES` default `LocMemCache`; add `RATELIMIT_USE_CACHE = "default"`, `RATELIMIT_ENABLE = env.bool("RATELIMIT_ENABLE", default=True)`, `RATELIMIT_VIEW = "registry.views.ratelimited"`.
  - Add `PUBLIC_VERIFY_RATE = env("PUBLIC_VERIFY_RATE", default="30/m")`, `LICENCE_EXPIRY_WARNING_DAYS = env.int("LICENCE_EXPIRY_WARNING_DAYS", default=180)`, `CARD_LINK_MAX_AGE = env.int("CARD_LINK_MAX_AGE", default=604800)`, `CARD_LINK_SALT = "registry.card"`.
  - Add `DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@example.com")`.
  - Document `PUBLIC_VERIFY_RATE`, `LICENCE_EXPIRY_WARNING_DAYS`, `CARD_LINK_MAX_AGE`, `RATELIMIT_ENABLE` in `.env.example`.
- **Mirror**: `config/settings.py:7-11`, `config/settings.py:18-38`, `config/settings.py:110-114`.
- **Validate**: after the normal requirements refresh, `python manage.py check`.

### Task 2: Implement state transitions, audit, flag, and rejection email

- **File**: `registry/services.py`
- **Action**: UPDATE
- **Implement**:
  - Add `ALLOWED_TRANSITIONS` keyed by `Nurse.RecordStatus`.
  - Add `transition_nurse(actor, nurse, new_status, reason="")` using `transaction.atomic()` and `select_for_update()`.
  - Reject non-officer actors with `PermissionDenied`.
  - Reject invalid transitions and missing reasons with `ValidationError`; no state change on failure.
  - For `flagged`, create a `Flag` row with `raised_by=actor` and the reason.
  - Write `LogEntry.objects.log_create(...)` with `action=LogEntry.Action.UPDATE`, `changes={"record_status": [old, new]}`, `additional_data={"reason": reason}`, `actor=actor`, `force_log=True`.
  - Add `approve_nurse`, `reject_nurse`, and `flag_nurse` wrappers.
  - On reject, call `send_mail` with `templates/email/registration_rejected.txt`; catch/log failures so the transition commits.
- **Mirror**: `registry/services.py:1-19`, `registry/models.py:177-200`.
- **Validate**: `python manage.py test registry.tests.ReviewActionTests`.

### Task 3: Add NANNM ID issuance, immutability, public status, and public URL helper

- **File**: `registry/services.py`, `registry/models.py`
- **Action**: UPDATE
- **Implement**:
  - Add `next_nanm_id()` returning `PLT-NUR-{sequence:06d}` from the maximum existing suffix inside the caller's transaction.
  - In `approve_nurse`, issue the ID only when `nanm_id` is empty; preserve an existing ID on re-approval.
  - Add `public_verify_url(nanm_id)` using `settings.PUBLIC_BASE_URL`.
  - Add `public_licence_status(nurse, today=None)` returning the seven public labels plus `Rejected` for completeness.
  - Override `Nurse.save()` to raise `ValidationError` if an existing `nanm_id` changes. Keep `nanm_id` read-only in admin.
- **Mirror**: `registry/models.py:40`, `registry/models.py:78-105`, `config/settings.py:110`.
- **Validate**: `python manage.py test registry.tests.NanmIdTests`.

### Task 4: Add admin approve/reject/flag actions with confirmation

- **File**: `registry/forms.py`, `registry/admin.py`, `templates/admin_review_confirm.html`
- **Action**: UPDATE/CREATE
- **Implement**:
  - Add `ReasonForm` with required `reason`.
  - Add `approve_selected`, `reject_selected`, `flag_selected` to `NurseAdmin.actions`.
  - Approve handles one selected nurse; if multiple are selected, show an admin error instead of partially approving.
  - Approve confirmation POST uses `post=yes`; on success call `approve_nurse` and redirect to `registry:approval_confirmation`.
  - Reject/flag confirmation validates `ReasonForm`; on success call the service for each selected nurse and show success/error messages.
  - Use `admin.helpers.ACTION_CHECKBOX_NAME` for `_selected_action`.
  - Keep `record_status` and `nanm_id` read-only; do not add direct status fields.
- **Mirror**: `registry/admin.py:40-64`, `registry/views.py:24-43`, `templates/base.html:1-20`.
- **Validate**: `python manage.py test registry.tests.AdminReviewActionTests`.

### Task 5: Add QR, public photo, card, signed link, and approval confirmation views

- **File**: `registry/views.py`, `registry/urls.py`, `templates/card.html`, `templates/card_invalid.html`, `templates/approval_confirmation.html`, `templates/base.html`, `static/css/card.css`
- **Action**: UPDATE/CREATE
- **Implement**:
  - `nurse_qr(request, nanm_id)` returns PNG bytes with `image/png` and `Cache-Control: no-store`; 404 for unknown or unissued IDs.
  - `public_nurse_photo(request, nanm_id)` serves the photo through `_serve_media`; 404 when absent.
  - `card(request, pk)` requires login and officer-or-above; `signed_card(request, token)` requires a valid `signing.loads(... max_age=settings.CARD_LINK_MAX_AGE)`.
  - Invalid/expired signed links render `card_invalid.html` with HTTP 400.
  - `approval_confirmation(request, pk)` requires login and officer-or-above, 404 unless approved with an ID, and exposes direct/signed card URLs plus email action.
  - `email_card_link(request, pk)` is POST-only, requires officer-or-above, sends the signed card link, and redirects back.
  - Card context includes name, photo URL, NANNM ID, expiry, public status, and QR URL. No sensitive fields.
  - Add `{% block extra_head %}{% endblock %}` to `base.html` and a verification nav link.
  - Card CSS: `85.6mm x 54mm` print size, one page, readable A4 fallback, hide navigation/buttons in print.
- **Mirror**: `registry/views.py:55-90`, `registry/urls.py:1-21`, `templates/base.html:1-20`.
- **Validate**: `python manage.py test registry.tests.CardTests`.

### Task 6: Add shared public serializer, API endpoint, and web verification

- **File**: `api/__init__.py`, `api/apps.py`, `api/serializers.py`, `api/views.py`, `api/urls.py`, `config/urls.py`, `registry/views.py`, `registry/urls.py`, `templates/verify.html`
- **Action**: CREATE/UPDATE
- **Implement**:
  - Add `api` to `INSTALLED_APPS` now that the package exists.
  - `PublicNurseSerializer` fields: `nanm_id`, `full_name`, `photo_url`, `licence_status`, `licence_expiry`, `employer`, `record_status`.
  - `photo_url` uses `reverse("registry:public_nurse_photo", args=[obj.nanm_id])`; empty string when no photo.
  - API `GET /api/v1/verify/<nanm_id>/` returns the serializer payload, `404 {"detail": "Not registered"}` for unknown IDs, and `AllowAny`.
  - Web `verify` renders the form; POST redirects to canonical `verify_result`.
  - `verify_result` uses the same serializer; unknown ID renders “Not registered”.
  - Include `path("api/v1/", include("api.urls"))` in `config/urls.py`.
  - `verify.html` shows only the allowed public fields and a hidden honeypot.
- **Mirror**: `.agents/PRDs/PRD.md:493-511`, `registry/views.py:20-52`, `config/urls.py:1-6`.
- **Validate**: `python manage.py test api.tests registry.tests.PublicVerificationTests`.

### Task 7: Add rate limiting, honeypot rejection, and 429 handler

- **File**: `config/settings.py`, `registry/views.py`, `api/views.py`, `templates/verify.html`
- **Action**: UPDATE
- **Implement**:
  - Add `public_verify_rate()` returning `settings.PUBLIC_VERIFY_RATE` for `django-ratelimit`.
  - Apply `@ratelimit(key="ip", rate=public_verify_rate, method=["GET", "POST"], block=True)` to public verification form/result, public photo, QR, and API.
  - Add `ratelimited(request, exception=None)` returning `HttpResponse("Too many requests. Try again later.", status=429)`.
  - Honeypot `website`: if present and non-empty, return HTTP 400 before lookup.
  - No public list/search endpoint.
  - Ensure the public path uses `select_related("employer")` and avoids N+1 queries.
- **Mirror**: `.agents/stories/plateau-nurse-register-stories.md:589-621`, `registry/views.py:76-90`.
- **Validate**: `python manage.py test registry.tests.PublicRateLimitTests api.tests`.

### Task 8: Add Day 2 tests

- **File**: `registry/tests.py`, `api/tests.py`
- **Action**: UPDATE/CREATE
- **Implement**:
  - `ReviewActionTests`: approve pending issues ID and audit; reject without reason blocked; reject with reason emails and audits; flag creates `Flag` and audits; invalid transition leaves state unchanged; non-officer denied.
  - `NanmIdTests`: sequential unique IDs, format, immutable after issue, QR returns PNG signature, public URL uses `PUBLIC_BASE_URL`.
  - `AdminReviewActionTests`: actions available, approval confirmation redirect, reject/flag reason validation, read-only status.
  - `CardTests`: direct card requires login; officer card 200; signed link 200 without login; tampered token 400; expired token 400 via `override_settings(CARD_LINK_MAX_AGE=-1)`; revoked/expired labels.
  - `PublicVerificationTests`: valid fields, unknown “Not registered”, sensitive fields absent, expired/flagged/suspended/revoked labels, API same payload, API 404, honeypot 400.
  - `PublicRateLimitTests`: `override_settings(PUBLIC_VERIFY_RATE="2/m", RATELIMIT_ENABLE=True)`, clear cache, assert 429; default tests use `RATELIMIT_ENABLE=False`.
  - For flagged public verification, create a nurse and assign a test `nanm_id` manually because seeded flagged nurses have no ID.
- **Mirror**: `registry/tests.py:63-131`, `registry/tests.py:1-40`.
- **Validate**: `python manage.py test`.

### Task 9: Document and run the Day 2 smoke path

- **File**: `README.md`, `.env.example`
- **Action**: UPDATE
- **Implement**:
  - Document `/verify/`, `/api/v1/verify/<nanm_id>/`, card routes, signed link expiry, and rate-limit setting.
  - Add the demo path: approve a seeded pending nurse, open confirmation, print card, copy signed link, scan QR, verify publicly, call API.
  - Note that new dependencies must be added through `requirements.txt`; do not install ad hoc packages.
  - Note that rejection email uses Django's email backend and full SMTP setup remains Day 3.
- **Mirror**: `README.md:1-40`.
- **Validate**: `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py test`, then manual smoke.

---

## Risks

| Risk | Mitigation |
|------|------------|
| `djangorestframework`, `qrcode`, or `django-ratelimit` absent from the current `.venv` | Add to `requirements.txt`; refresh the environment through the normal workflow before running Day 2 tests. Do not `pip install` ad hoc. |
| NANNM ID race under concurrent approvals | Generate inside `transaction.atomic()` with `select_for_update()`, rely on unique constraint, retry once on `IntegrityError`. |
| `approved` constraint fails if status saves before ID | Issue `nanm_id` and set `approved` in the same save. |
| Signed link expiry test is time-dependent | Use `override_settings(CARD_LINK_MAX_AGE=-1)` with a valid token instead of sleeping or freezing time. |
| Rate-limit state leaks between tests | Set `RATELIMIT_ENABLE=False` in the test base; enable only in the 429 test and clear the cache. |
| Public photo route becomes an enumeration surface | Require exact `nanm_id`; no list/search; keep rate limiting; never expose pending records without IDs. |
| Jinja2 picks up a Django-syntax admin template | Keep the admin action confirmation as a root Jinja template; do not place Django-syntax admin templates in `templates/`. |
| Rejection email failure rolls back the decision | Catch/log email exceptions after the status save; tests use locmem. |
| Seeded flagged nurses have no NANNM ID | Public flagged test must assign a test ID; do not change seed semantics for Day 2. |
| Card QR/photo URLs break when `PUBLIC_BASE_URL` has a trailing slash | Normalize with `.rstrip("/")` in the URL helper; use `reverse` for in-app image URLs. |
| Card prints across multiple pages | Fixed card dimensions, `@media print`, one-page fallback, hide non-card elements. |

---

## Validation

```bash
# Activate the existing environment
source .venv/bin/activate

# After requirements are provisioned through the normal workflow
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Manual smoke path:

1. `python manage.py seed_demo --reset`
2. Log in as an officer in admin.
3. Approve a pending nurse; confirm the next `PLT-NUR-` ID is issued.
4. Open the approval confirmation page; print the card; copy the signed link.
5. Open the signed link in a private window without login.
6. Scan/open the QR URL; confirm the public page shows name, photo, status, expiry, employer, and ID only.
7. Call `/api/v1/verify/<nanm_id>/`; confirm the same fields.
8. Submit an unknown ID; confirm “Not registered”.
9. Exceed the configured rate limit; confirm HTTP 429.
10. Confirm `NIN`, licence number, phone, email, and ward never appear publicly.

---

## Acceptance Criteria

- [ ] Pending nurse approval sets `approved`, issues a unique immutable `PLT-NUR-` ID, and writes an audit entry.
- [ ] Reject without reason is blocked; reject with reason sets `rejected`, emails the nurse, and audits.
- [ ] Flag with reason sets `flagged`, creates a `Flag`, and audits.
- [ ] Invalid transitions leave the record unchanged.
- [ ] Approved nurse QR endpoint returns a PNG resolving to `PUBLIC_BASE_URL/verify/<nanm_id>/`.
- [ ] Card shows name, photo, NANNM ID, expiry, status, and QR; direct access requires login; signed links work for 7 days and fail clearly when tampered or expired.
- [ ] Public verification shows only name, photo, licence status, expiry, employer, and ID; unknown IDs show “Not registered”.
- [ ] API returns the same minimal fields as JSON and 404 for unknown IDs.
- [ ] Public verification is rate-limited, rejects honeypot submissions, and has no list/search endpoint.
- [ ] `python manage.py check`, `makemigrations --check --dry-run`, and `python manage.py test` pass after dependency provisioning.
