# Jira Stories: Plateau State Nurse Registry and Licence Verification Platform

**Source PRD:** `.agents/PRDs/PRD.md` (v2.0, 4-day MVP)
**Generated:** 1 November 2026
**Total stories:** 30
**Delivery window:** 4 working days

---

## Summary

| ID | Title | Type | Jira Type | Priority | Complexity | Phase | Blocked By |
|---|---|---|---|---|---|---|---|
| PNR-01 | Project scaffold and configuration | Technical | Task | High | Small | Day 1 | — |
| PNR-02 | Core data models and migrations | Technical | Task | High | Medium | Day 1 | PNR-01 |
| PNR-03 | NIN encryption and masking | Technical | Task | High | Small | Day 1 | PNR-02 |
| PNR-04 | Django admin back office | Technical | Task | High | Medium | Day 1 | PNR-02 |
| PNR-05 | Roles, groups, and HR employer link | Technical | Task | High | Small | Day 1 | PNR-02 |
| PNR-06 | Protected local media storage | Technical | Task | High | Small | Day 1 | PNR-02 |
| PNR-07 | Officer registration form with consent | Feature | Story | High | Medium | Day 1 | PNR-01, PNR-02, PNR-05, PNR-06 |
| PNR-08 | Licence scan and selfie upload | Feature | Story | High | Medium | Day 1 | PNR-07, PNR-06 |
| PNR-09 | Duplicate detection warning | Feature | Story | Medium | Small | Day 1 | PNR-07 |
| PNR-10 | Seed demo data command | Technical | Task | High | Medium | Day 1 | PNR-02, PNR-05, PNR-06 |
| PNR-11 | Review actions and state transitions | Feature | Story | High | Medium | Day 2 | PNR-12, PNR-04, PNR-05 |
| PNR-12 | NANNM ID generation and QR endpoint | Feature | Story | High | Small | Day 2 | PNR-02 |
| PNR-13 | Printable ID card | Feature | Story | High | Small | Day 2 | PNR-12, PNR-06 |
| PNR-14 | Approval confirmation and signed card link | Feature | Story | High | Medium | Day 2 | PNR-13, PNR-01 |
| PNR-15 | Public verification page and API | Feature | Story | High | Medium | Day 2 | PNR-12, PNR-02 |
| PNR-16 | Public rate limiting and anti-enumeration | Technical | Task | High | Small | Day 2 | PNR-15 |
| PNR-17 | HR employer-scoped admin view | Feature | Story | High | Medium | Day 3 | PNR-05, PNR-04, PNR-02 |
| PNR-18 | Employment confirmation action | Feature | Story | High | Small | Day 3 | PNR-17 |
| PNR-19 | Renewal upload and approval | Feature | Story | High | Medium | Day 3 | PNR-11, PNR-12 |
| PNR-20 | Licence status computation and filters | Feature | Story | High | Small | Day 3 | PNR-02 |
| PNR-21 | Expiry reminder command with dedupe | Feature | Story | High | Medium | Day 3 | PNR-20, PNR-22 |
| PNR-22 | SMTP configuration and expiry email | Technical | Task | High | Small | Day 3 | PNR-01 |
| PNR-23 | Audit logging and admin viewer | Technical | Task | High | Small | Day 3 | PNR-02, PNR-04 |
| PNR-24 | CSV export admin action | Feature | Story | High | Small | Day 3 | PNR-04, PNR-23 |
| PNR-25 | Suspend and revoke NANNM ID | Feature | Story | High | Small | Day 3 | PNR-11, PNR-12 |
| PNR-26 | Demo script, README, backup and reset | Technical | Task | High | Small | Day 4 | PNR-11 to PNR-25 |
| PNR-27 | Demo data polish and demo-mode banner | Technical | Task | Low | Small | Day 4 | PNR-10, PNR-26 |
| PNR-28 | Smoke test suite and bug-fix pass | Technical | Task | High | Medium | Day 4 | PNR-11 to PNR-25 |
| PNR-29 | Optional VPS deployment configuration | Technical | Task | Low | Medium | Day 4 (stretch) | PNR-26 |
| PNR-30 | Thin API for core records | Technical | Task | Medium | Medium | Day 4 | PNR-02, PNR-12, PNR-15, PNR-19 |

---

## Day 1: Foundation and Registration

### PNR-01: Project scaffold and configuration

**Type:** Technical
**Jira Type:** Task
**Priority:** High
**Complexity:** Small
**Phase:** Day 1
**Labels:** `backend`, `setup`
**PRD Reference:** Sections 6, 8, 9

#### Description

As a developer, I want a runnable Django project with Jinja2 templates, environment configuration, and a SQLite/PostgreSQL switch, so that the team can build and demo without Docker.

#### Acceptance Criteria

- [ ] Given a clean clone, when I install requirements and run `python manage.py migrate`, then the app starts with `runserver`.
- [ ] Given no `DATABASE_URL`, when settings load, then SQLite at `db.sqlite3` is used.
- [ ] Given `DATABASE_URL`, when settings load, then PostgreSQL is used.
- [ ] Given `DJANGO_DEBUG` is unset, when settings load, then debug is false.
- [ ] Given a request to `/`, when templates render, then the Jinja2 base page loads without error.

#### Technical Notes

- Files: `config/settings.py`, `config/urls.py`, `requirements.txt`, `.env.example`, `templates/base.html`, `manage.py`.
- Use `django-environ`; do not write a custom env parser.
- Keep settings in one file for MVP; no settings package.
- Add `PUBLIC_BASE_URL` and `REMINDER_DAYS` defaults.

#### Dependencies

- Blocked by: none
- Blocks: PNR-02 through PNR-30

---

### PNR-02: Core data models and migrations

**Type:** Technical
**Jira Type:** Task
**Priority:** High
**Complexity:** Medium
**Phase:** Day 1
**Labels:** `backend`, `database`
**PRD Reference:** Sections 6, 15.1, 15.2

#### Description

As a developer, I want the core registry models and migrations, so that registration, review, verification, and reporting have a stable data layer.

#### Acceptance Criteria

- [ ] Given a fresh database, when migrations run, then `Employer`, `Nurse`, `LicenceDocument`, `Flag`, and `Notification` tables exist.
- [ ] Given an approved nurse, when saved, then `nanm_id` is unique and non-null.
- [ ] Given a duplicate reminder for the same nurse, type, and expiry, when saved, then the database rejects it.
- [ ] Given a nurse, when `record_status` is set, then only the allowed choices are accepted.
- [ ] Given model changes, when migrations are checked, then no pending migrations remain.

#### Technical Notes

- Files: `registry/models.py`, `registry/migrations/`.
- `Nurse` fields per PRD 15.1; current employer only; no employment history table.
- Add indexes on `nanm_id`, `licence_expiry`, `record_status`, and `employer`.
- Use `TextChoices` for statuses and document types.

#### Dependencies

- Blocked by: PNR-01
- Blocks: PNR-03 through PNR-30

---

### PNR-03: NIN encryption and masking

**Type:** Technical
**Jira Type:** Task
**Priority:** High
**Complexity:** Small
**Phase:** Day 1
**Labels:** `backend`, `security`
**PRD Reference:** Sections 9, 15.1

#### Description

As a system owner, I want NIN encrypted at rest and masked by default, so that the registry meets NDPA expectations and limits exposure.

#### Acceptance Criteria

- [ ] Given a nurse with a NIN, when saved, then the database stores ciphertext, not the plaintext NIN.
- [ ] Given an authorized officer, when viewing a nurse, then the NIN can be revealed and the reveal is audited.
- [ ] Given an HR or public view, when a nurse is rendered, then only `nin_last4` is available.
- [ ] Given a missing or invalid `NIN_ENCRYPTION_KEY`, when the app starts, then it fails with a clear configuration error.
- [ ] Given encryption and decryption, when round-tripped in tests, then the original NIN is recovered.

#### Technical Notes

- Files: `registry/crypto.py`, `registry/models.py`, `registry/tests.py`.
- Use `cryptography.fernet.Fernet`.
- Store `nin_encrypted` and `nin_last4`; never store plaintext.
- Add a `reveal_nin` service that checks role and writes an audit event.

#### Dependencies

- Blocked by: PNR-02
- Blocks: PNR-07, PNR-17

---

### PNR-04: Django admin back office

**Type:** Technical
**Jira Type:** Task
**Priority:** High
**Complexity:** Medium
**Phase:** Day 1
**Labels:** `backend`, `admin`
**PRD Reference:** Sections 6, 7.2, 12

#### Description

As an officer or supervisor, I want the registry models in Django admin with search, filters, and safe read-only fields, so that the back office works without custom screens.

#### Acceptance Criteria

- [ ] Given a superuser, when opening admin, then all registry models are listed.
- [ ] Given the nurse list, when filtering by status, employer, or expiry window, then results are correct.
- [ ] Given a nurse detail, when opened, then `nanm_id`, `created_at`, and audit fields are read-only.
- [ ] Given a licence document, when opened, then the scan preview is visible.
- [ ] Given a non-staff user, when opening admin, then access is denied.

#### Technical Notes

- Files: `registry/admin.py`.
- Use `list_display`, `list_filter`, `search_fields`, `readonly_fields`.
- Keep image previews simple; no custom admin theme.
- Do not add custom dashboard templates.

#### Dependencies

- Blocked by: PNR-02
- Blocks: PNR-11, PNR-17, PNR-23, PNR-24

---

### PNR-05: Roles, groups, and HR employer link

**Type:** Technical
**Jira Type:** Task
**Priority:** High
**Complexity:** Small
**Phase:** Day 1
**Labels:** `backend`, `security`
**PRD Reference:** Sections 7.4, 9, 15.1

#### Description

As a system owner, I want Django groups for Officer, Supervisor, Super Admin, and HR, with HR linked to employers, so that permissions and scoping are enforced consistently.

#### Acceptance Criteria

- [ ] Given a fresh database, when setup runs, then the four groups exist with the intended permissions.
- [ ] Given an officer, when attempting to revoke an ID, then permission is denied.
- [ ] Given a supervisor, when approving a renewal, then permission is allowed.
- [ ] Given an HR user linked to one employer, when querying nurses, then only that employer's nurses are returned.
- [ ] Given a user in no group, when accessing staff views, then access is denied.

#### Technical Notes

- Files: `registry/permissions.py`, `registry/migrations/`, `registry/tests.py`.
- Use Django built-in `Group` and `Permission`; do not create a custom role model.
- Add `Employer.hr_users` M2M.
- Create groups in a data migration or `setup_groups` command.

#### Dependencies

- Blocked by: PNR-02
- Blocks: PNR-07, PNR-11, PNR-17, PNR-25

---

### PNR-06: Protected local media storage

**Type:** Technical
**Jira Type:** Task
**Priority:** High
**Complexity:** Small
**Phase:** Day 1
**Labels:** `backend`, `security`
**PRD Reference:** Sections 7.1, 9

#### Description

As a system owner, I want licence scans and selfies stored outside the web root and served only through permission-checked views, so that private documents are not publicly accessible.

#### Acceptance Criteria

- [ ] Given an uploaded licence scan, when saved, then the file is under `media/` and not under `static/`.
- [ ] Given a direct request to the media file path, when the user is not authorized, then access is denied.
- [ ] Given an authorized officer, when requesting a document, then the file is served.
- [ ] Given a path traversal attempt, when requesting a file, then the request is rejected.
- [ ] Given a public verification request, when rendering, then no private document URL is exposed.

#### Technical Notes

- Files: `config/settings.py`, `registry/views.py`, `registry/urls.py`.
- Use Django `FileSystemStorage` and `FileResponse`.
- Do not add `django-storages` or S3 in MVP.
- Serve media only through a view that checks group and object ownership.

#### Dependencies

- Blocked by: PNR-02
- Blocks: PNR-07, PNR-08, PNR-13

---

### PNR-07: Officer registration form with consent

**Type:** Feature
**Jira Type:** Story
**Priority:** High
**Complexity:** Medium
**Phase:** Day 1
**Labels:** `backend`, `frontend`, `registration`
**PRD Reference:** Sections 5 (US-01), 7.1

#### Description

As a field officer, I want to register a nurse in one form with details and consent, so that the nurse enters the register without needing an account.

#### Acceptance Criteria

- [ ] Given an unauthenticated user, when opening the registration page, then they are redirected to login.
- [ ] Given an officer, when submitting valid details, then a `pending` nurse is created and linked to the officer.
- [ ] Given the consent checkbox is unchecked, when submitting, then the form is rejected with a clear error.
- [ ] Given a successful submission, when consent is recorded, then `consent_at` is set.
- [ ] Given a successful submission, when the confirmation page loads, then a reference and pending status are shown.

#### Technical Notes

- Files: `registry/forms.py`, `registry/views.py`, `registry/urls.py`, `templates/register.html`.
- Use Django `ModelForm` and server-side validation.
- Required fields per PRD 7.1; phone and email validated.
- Keep the page mobile-first; one column.

#### Dependencies

- Blocked by: PNR-01, PNR-02, PNR-05, PNR-06
- Blocks: PNR-08, PNR-09

---

### PNR-08: Licence scan and selfie upload

**Type:** Feature
**Jira Type:** Story
**Priority:** High
**Complexity:** Medium
**Phase:** Day 1
**Labels:** `backend`, `frontend`, `uploads`
**PRD Reference:** Sections 5 (US-01), 7.1

#### Description

As a field officer, I want to upload a licence scan and capture a live selfie, so that the reviewer can verify identity and licence authenticity.

#### Acceptance Criteria

- [ ] Given a PDF, JPG, or PNG licence scan under 10 MB, when uploaded, then the file is accepted and linked to the nurse.
- [ ] Given a file over 10 MB or an unsupported type, when uploaded, then the form shows a field-level error.
- [ ] Given a device with a camera, when capturing a selfie, then the captured image is attached to the submission.
- [ ] Given a device without camera access, when capturing, then a file-upload fallback is available.
- [ ] Given a stored document, when viewed by an officer, then it renders through the protected media view.

#### Technical Notes

- Files: `registry/forms.py`, `registry/views.py`, `templates/register.html`.
- Use `getUserMedia` with a file input fallback; no JavaScript framework.
- Validate content type, extension, size, and image parsing server-side.
- Store selfie on `Nurse.photo`; store licence scan on `LicenceDocument.file`.

#### Dependencies

- Blocked by: PNR-07, PNR-06
- Blocks: PNR-11, PNR-13

---

### PNR-09: Duplicate detection warning

**Type:** Feature
**Jira Type:** Story
**Priority:** Medium
**Complexity:** Small
**Phase:** Day 1
**Labels:** `backend`, `validation`
**PRD Reference:** Sections 7.1

#### Description

As an officer, I want a warning when a NIN or licence number already exists, so that I can catch duplicates without being blocked on legitimate cases.

#### Acceptance Criteria

- [ ] Given an existing NIN, when a new registration uses it, then the form shows a duplicate warning.
- [ ] Given an existing licence number, when a new registration uses it, then the form shows a duplicate warning.
- [ ] Given a duplicate warning, when the officer confirms, then the record can still be submitted.
- [ ] Given a duplicate record, when viewed in admin, then it is visibly marked.
- [ ] Given no duplicate, when submitting, then no warning is shown.

#### Technical Notes

- Files: `registry/forms.py`, `registry/admin.py`, `registry/models.py`.
- Do not add a hard unique constraint on NIN or licence number; duplicates can be legitimate data-entry issues.
- Add a `possible_duplicate` flag or computed admin display.

#### Dependencies

- Blocked by: PNR-07
- Blocks: PNR-11

---

### PNR-10: Seed demo data command

**Type:** Technical
**Jira Type:** Task
**Priority:** High
**Complexity:** Medium
**Phase:** Day 1
**Labels:** `backend`, `demo`
**PRD Reference:** Sections 7.9, 12

#### Description

As a presenter, I want a single command that creates realistic fake data, so that the demo is repeatable and does not depend on manual entry.

#### Acceptance Criteria

- [ ] Given an empty database, when `seed_demo` runs, then it creates 4 employers, 1 super admin, 2 officers, 1 supervisor, 2 HR users, and 60 nurses.
- [ ] Given the seeded nurses, when listed, then they cover green, yellow, red, pending, flagged, suspended, and revoked states.
- [ ] Given seeded records, when viewed, then placeholder licence scans and selfies render.
- [ ] Given a non-empty database, when `seed_demo` runs without `--reset`, then it refuses and explains why.
- [ ] Given a successful seed, when the command finishes, then it prints login credentials and a summary.

#### Technical Notes

- Files: `registry/management/commands/seed_demo.py`.
- Use fixed name and employer lists; no Faker dependency.
- Generate placeholder images with Pillow.
- Use fake NINs and licence numbers; no real PII.

#### Dependencies

- Blocked by: PNR-02, PNR-05, PNR-06
- Blocks: PNR-26, PNR-27

---

## Day 2: Review, ID, and Public Verification

### PNR-11: Review actions and state transitions

**Type:** Feature
**Jira Type:** Story
**Priority:** High
**Complexity:** Medium
**Phase:** Day 2
**Labels:** `backend`, `admin`, `workflow`
**PRD Reference:** Sections 5 (US-02), 7.2, 15.2

#### Description

As an officer, I want to approve, reject, or flag a pending nurse from admin, so that only verified nurses enter the public register.

#### Acceptance Criteria

- [ ] Given a pending nurse, when an officer approves, then the record becomes `approved` and a NANNM ID is issued.
- [ ] Given a pending nurse, when an officer rejects without a reason, then the action is blocked.
- [ ] Given a pending nurse, when an officer rejects with a reason, then the record becomes `rejected` and the nurse is emailed.
- [ ] Given a pending nurse, when an officer flags with a reason, then the record becomes `flagged`.
- [ ] Given an invalid transition, when attempted, then the action is rejected and no state changes.

#### Technical Notes

- Files: `registry/admin.py`, `registry/services.py`, `registry/tests.py`.
- Implement transitions in `services.py` with `transaction.atomic()`.
- Use admin actions with an intermediate confirmation page for reasons.
- Do not allow direct status edits in admin; use actions only.

#### Dependencies

- Blocked by: PNR-12, PNR-04, PNR-05
- Blocks: PNR-19, PNR-25, PNR-26

---

### PNR-12: NANNM ID generation and QR endpoint

**Type:** Feature
**Jira Type:** Story
**Priority:** High
**Complexity:** Small
**Phase:** Day 2
**Labels:** `backend`, `qr`
**PRD Reference:** Sections 6, 7.7

#### Description

As an approved nurse, I want a unique NANNM ID and QR code, so that I can be identified and verified quickly.

#### Acceptance Criteria

- [ ] Given an approval, when the ID is issued, then it matches `PLT-NUR-` plus a zero-padded sequence.
- [ ] Given an issued ID, when the nurse record is updated, then the ID cannot be changed.
- [ ] Given an approved nurse, when requesting the QR endpoint, then a PNG is returned.
- [ ] Given the QR content, when scanned, then it resolves to `PUBLIC_BASE_URL/verify/<nanm_id>`.
- [ ] Given two approvals, when IDs are issued, then they are unique.

#### Technical Notes

- Files: `registry/services.py`, `registry/views.py`, `registry/urls.py`.
- Use `qrcode` and `Pillow`; generate on request, do not store QR files.
- Use a database sequence or max-ID-plus-one inside a transaction.

#### Dependencies

- Blocked by: PNR-02
- Blocks: PNR-11, PNR-13, PNR-15, PNR-25

---

### PNR-13: Printable ID card

**Type:** Feature
**Jira Type:** Story
**Priority:** High
**Complexity:** Small
**Phase:** Day 2
**Labels:** `frontend`, `card`
**PRD Reference:** Sections 5 (US-03), 7.7

#### Description

As an officer, I want a print-ready ID card for an approved nurse, so that the nurse leaves the drive with proof of registration.

#### Acceptance Criteria

- [ ] Given an approved nurse, when the card page loads, then it shows name, photo, NANNM ID, expiry, status, and QR.
- [ ] Given a print dialog, when printing, then the card uses a credit-card-sized print stylesheet.
- [ ] Given a standard printer, when printing on A4, then a fallback layout keeps the card readable.
- [ ] Given an unauthenticated user, when requesting the card page directly, then access is denied unless the request uses a valid signed link.
- [ ] Given a revoked or expired nurse, when printing, then the card shows the correct state.

#### Technical Notes

- Files: `templates/card.html`, `registry/views.py`, `static/css/card.css`.
- Use CSS `@media print`; no PDF library.
- Embed the QR image from the QR endpoint.
- Keep the card to one page.

#### Dependencies

- Blocked by: PNR-12, PNR-06
- Blocks: PNR-14

---

### PNR-14: Approval confirmation and signed card link

**Type:** Feature
**Jira Type:** Story
**Priority:** High
**Complexity:** Medium
**Phase:** Day 2
**Labels:** `backend`, `frontend`, `email`
**PRD Reference:** Sections 5 (US-03), 7.7

#### Description

As an officer, I want a confirmation page with print and share options after approval, so that the nurse can receive a card even without a login.

#### Acceptance Criteria

- [ ] Given a successful approval, when the confirmation page loads, then it shows **Print card** and **Copy card link**.
- [ ] Given the card link, when generated, then it is signed and expires after 7 days.
- [ ] Given a valid card link, when opened without login, then the card page renders.
- [ ] Given an expired or tampered link, when opened, then a clear error is shown.
- [ ] Given the officer chooses email, when the nurse has an email address, then the card link is sent.

#### Technical Notes

- Files: `registry/views.py`, `registry/services.py`, `templates/card.html`.
- Use `django.core.signing` with a timestamp; no external token service.
- Do not expose the card from the public verification page.
- Reuse the Django email backend.

#### Dependencies

- Blocked by: PNR-13, PNR-01
- Blocks: PNR-26

---

### PNR-15: Public verification page and API

**Type:** Feature
**Jira Type:** Story
**Priority:** High
**Complexity:** Medium
**Phase:** Day 2
**Labels:** `backend`, `frontend`, `api`
**PRD Reference:** Sections 5 (US-03), 7.3, 10

#### Description

As a member of the public, I want to verify a nurse by NANNM ID or QR, so that I can confirm registration and licence status in seconds.

#### Acceptance Criteria

- [ ] Given a valid NANNM ID, when submitted, then name, photo, licence status, expiry, employer name, and ID are shown.
- [ ] Given an unknown ID, when submitted, then "Not registered" is shown.
- [ ] Given any public result, when rendered, then NIN, licence number, phone, email, ward, and address are absent.
- [ ] Given a revoked, suspended, flagged, or expired nurse, when verified, then the correct state is shown.
- [ ] Given the API endpoint, when called with a valid ID, then the same minimal fields are returned as JSON.

#### Technical Notes

- Files: `registry/views.py`, `templates/verify.html`, `api/views.py`, `api/serializers.py`, `api/urls.py`.
- Reuse one serializer for the public response.
- QR resolution uses the same view.
- No public list or search-by-name endpoint.

#### Dependencies

- Blocked by: PNR-12, PNR-02
- Blocks: PNR-16, PNR-30

---

### PNR-16: Public rate limiting and anti-enumeration

**Type:** Technical
**Jira Type:** Task
**Priority:** High
**Complexity:** Small
**Phase:** Day 2
**Labels:** `backend`, `security`
**PRD Reference:** Sections 7.3, 9

#### Description

As a system owner, I want public verification rate-limited and resistant to enumeration, so that bulk scraping is impractical.

#### Acceptance Criteria

- [ ] Given repeated requests from one IP above the limit, when the limit is exceeded, then `429` is returned.
- [ ] Given a bot that fills the honeypot field, when submitting, then the request is rejected.
- [ ] Given a valid ID, when verified, then the response time stays under one second at p95 on seeded data.
- [ ] Given the public site, when searching for a list endpoint, then none exists.
- [ ] Given rate limiting, when configured, then the threshold is documented in settings.

#### Technical Notes

- Files: `config/settings.py`, `registry/views.py`, `api/views.py`.
- Use `django-ratelimit`; do not write a custom throttle.
- Add a hidden honeypot field to the verification form.
- Return generic messages for unknown IDs.

#### Dependencies

- Blocked by: PNR-15
- Blocks: PNR-28

---

## Day 3: HR, Renewal, Expiry, Audit, and Export

### PNR-17: HR employer-scoped admin view

**Type:** Feature
**Jira Type:** Story
**Priority:** High
**Complexity:** Medium
**Phase:** Day 3
**Labels:** `backend`, `admin`, `hr`
**PRD Reference:** Sections 5 (US-04), 7.4, 15.3

#### Description

As hospital HR, I want a read-only admin view scoped to my employer, so that I can check nurses without seeing other hospitals' staff.

#### Acceptance Criteria

- [ ] Given HR linked to Employer A, when opening the nurse list, then only Employer A nurses appear.
- [ ] Given HR linked to Employer A, when requesting an Employer B nurse by URL, then access is denied.
- [ ] Given an HR view, when a nurse is opened, then NIN, licence number, phone, email, and audit are hidden.
- [ ] Given an HR view, when a nurse is opened, then name, photo, ID, status, expiry, ward, cadre, specialty, and confirmation are shown.
- [ ] Given HR, when attempting to edit a nurse, then the form is read-only.

#### Technical Notes

- Files: `registry/admin.py`, `registry/permissions.py`, `registry/tests.py`.
- Override `get_queryset` using `request.user.employer_set`.
- Use `has_change_permission = False` for HR.
- Do not create a separate HR frontend in MVP.

#### Dependencies

- Blocked by: PNR-05, PNR-04, PNR-02
- Blocks: PNR-18

---

### PNR-18: Employment confirmation action

**Type:** Feature
**Jira Type:** Story
**Priority:** High
**Complexity:** Small
**Phase:** Day 3
**Labels:** `backend`, `admin`, `hr`
**PRD Reference:** Sections 5 (US-04), 7.4

#### Description

As hospital HR, I want to confirm that a nurse works at my hospital, so that the registry reflects verified employment.

#### Acceptance Criteria

- [ ] Given HR and a nurse at their employer, when confirming employment, then `employer_confirmed_at` and `employer_confirmed_by` are set.
- [ ] Given a confirmed nurse, when viewed, then a confirmation badge and date are shown.
- [ ] Given HR and a nurse at another employer, when attempting confirmation, then the action is denied.
- [ ] Given a confirmation, when the audit log is viewed, then the actor and timestamp are recorded.
- [ ] Given a previously confirmed nurse, when re-confirmed, then the timestamp updates.

#### Technical Notes

- Files: `registry/admin.py`, `registry/services.py`, `registry/tests.py`.
- Use an admin action with a confirmation step.
- Reuse the audit integration from PNR-23.

#### Dependencies

- Blocked by: PNR-17
- Blocks: PNR-28

---

### PNR-19: Renewal upload and approval

**Type:** Feature
**Jira Type:** Story
**Priority:** High
**Complexity:** Medium
**Phase:** Day 3
**Labels:** `backend`, `admin`, `renewal`
**PRD Reference:** Sections 5 (US-06), 7.6

#### Description

As an officer, I want to upload a renewed licence and have a supervisor approve it, so that the nurse's expiry updates without re-registration.

#### Acceptance Criteria

- [ ] Given an approved nurse, when an officer adds a renewal document with a new expiry, then the document is `pending`.
- [ ] Given a pending renewal, when a supervisor approves, then `licence_expiry` updates and status recomputes.
- [ ] Given a pending renewal, when an officer (not supervisor) attempts approval, then permission is denied.
- [ ] Given an approved renewal, when history is viewed, then the old document remains.
- [ ] Given a renewal, when completed, then the NANNM ID is unchanged.

#### Technical Notes

- Files: `registry/admin.py`, `registry/services.py`, `registry/models.py`, `registry/tests.py`.
- Add `LicenceDocument` inline to `NurseAdmin`.
- Approval action only for Supervisor and Super Admin.
- Reuse the status computation from PNR-20.

#### Dependencies

- Blocked by: PNR-11, PNR-12
- Blocks: PNR-30

---

### PNR-20: Licence status computation and filters

**Type:** Feature
**Jira Type:** Story
**Priority:** High
**Complexity:** Small
**Phase:** Day 3
**Labels:** `backend`, `admin`, `status`
**PRD Reference:** Sections 6, 7.5

#### Description

As an officer, I want licence colours computed from expiry and visible in admin, so that I can see who is licensed, expiring, or expired.

#### Acceptance Criteria

- [ ] Given more than 180 days to expiry, when status is computed, then it is green.
- [ ] Given 180 days or fewer, when status is computed, then it is yellow.
- [ ] Given a past expiry, when status is computed, then it is red.
- [ ] Given a pending record, when status is computed, then it is grey.
- [ ] Given a flagged, suspended, or revoked record, when status is computed, then it is black.
- [ ] Given the admin list, when filtering by colour, then results match the rules.

#### Technical Notes

- Files: `registry/models.py`, `registry/admin.py`, `registry/tests.py`.
- Use a `@property` or `annotate`; do not store the colour.
- Thresholds are constants in settings for MVP.
- Test the exact 180-day boundary.

#### Dependencies

- Blocked by: PNR-02
- Blocks: PNR-21, PNR-28

---

### PNR-21: Expiry reminder command with dedupe

**Type:** Feature
**Jira Type:** Story
**Priority:** High
**Complexity:** Medium
**Phase:** Day 3
**Labels:** `backend`, `email`, `notifications`
**PRD Reference:** Sections 5 (US-05), 7.5

#### Description

As a nurse, I want one email before my licence expires, so that I can renew with NMCN on time.

#### Acceptance Criteria

- [ ] Given a licence expiring within `REMINDER_DAYS`, when the command runs, then one email is sent to the nurse.
- [ ] Given a nurse already notified for the same expiry date, when the command reruns, then no second email is sent.
- [ ] Given a send failure, when the command finishes, then a `failed` notification row records the error.
- [ ] Given a licence outside the reminder window, when the command runs, then no email is sent.
- [ ] Given the command, when run manually, then it prints a summary of sent, skipped, and failed.

#### Technical Notes

- Files: `registry/management/commands/send_expiry_reminders.py`, `registry/models.py`, `registry/tests.py`.
- Use Django `send_mail`; no Celery.
- Unique constraint on (`nurse`, `type`, `licence_expiry`).
- Log failures without crashing the whole run.

#### Dependencies

- Blocked by: PNR-20, PNR-22
- Blocks: PNR-28

---

### PNR-22: SMTP configuration and expiry email

**Type:** Technical
**Jira Type:** Task
**Priority:** High
**Complexity:** Small
**Phase:** Day 3
**Labels:** `backend`, `email`, `config`
**PRD Reference:** Sections 8, 9

#### Description

As a system owner, I want Django's built-in email backend configured for SMTP, so that reminders send through any mail provider without an SDK.

#### Acceptance Criteria

- [ ] Given SMTP environment variables, when the app sends mail, then it uses `django.core.mail.backends.smtp.EmailBackend`.
- [ ] Given local development without SMTP, when mail is sent, then it uses the console backend.
- [ ] Given the expiry email, when rendered, then it includes the nurse's name, expiry date, and renewal instructions.
- [ ] Given missing SMTP settings in production, when the app starts, then it fails clearly.
- [ ] Given a test send, when the command runs, then the message is delivered to the configured inbox.

#### Technical Notes

- Files: `config/settings.py`, `templates/email/expiry_reminder.txt`, `.env.example`.
- Use plain-text email; no HTML template needed.
- Keep `DEFAULT_FROM_EMAIL` configurable.
- No provider SDK or API key.

#### Dependencies

- Blocked by: PNR-01
- Blocks: PNR-21

---

### PNR-23: Audit logging and admin viewer

**Type:** Technical
**Jira Type:** Task
**Priority:** High
**Complexity:** Small
**Phase:** Day 3
**Labels:** `backend`, `security`, `audit`
**PRD Reference:** Sections 7.8, 9

#### Description

As a super admin, I want privileged actions logged and viewable in admin, so that decisions are attributable and disputes can be answered.

#### Acceptance Criteria

- [ ] Given a nurse create, update, or delete, when saved, then an audit entry is written.
- [ ] Given an approve, reject, flag, suspend, revoke, or export action, when completed, then an audit entry names the actor and timestamp.
- [ ] Given a super admin, when opening the audit viewer, then entries can be filtered by actor and date.
- [ ] Given a non-superuser, when requesting the audit viewer, then access is denied.
- [ ] Given an audit entry, when viewed, then it cannot be edited or deleted by a normal admin.

#### Technical Notes

- Files: `registry/models.py`, `registry/admin.py`, `config/settings.py`.
- Use `django-auditlog`; do not build a custom audit table.
- Register `Nurse`, `LicenceDocument`, `Employer`, `Flag`, and `User`.
- Keep the default `LogEntry` admin.

#### Dependencies

- Blocked by: PNR-02, PNR-04
- Blocks: PNR-24

---

### PNR-24: CSV export admin action

**Type:** Feature
**Jira Type:** Story
**Priority:** High
**Complexity:** Small
**Phase:** Day 3
**Labels:** `backend`, `admin`, `export`
**PRD Reference:** Sections 5 (US-08), 7.8

#### Description

As a super admin, I want to export the nurse list as CSV, so that I can hand data to the council and answer oversight requests.

#### Acceptance Criteria

- [ ] Given a super admin, when exporting the filtered nurse list, then a CSV downloads.
- [ ] Given a non-superuser, when attempting export, then the action is not available.
- [ ] Given the CSV, when opened, then it includes NANNM ID, name, employer, ward, cadre, status, and expiry.
- [ ] Given the CSV, when inspected, then it does not include NIN.
- [ ] Given an export, when the audit log is viewed, then the export is recorded with actor and timestamp.

#### Technical Notes

- Files: `registry/admin.py`.
- Use Python `csv` and `HttpResponse`; no export library.
- Apply the same filters as the admin list.
- Keep the column set fixed for MVP.

#### Dependencies

- Blocked by: PNR-04, PNR-23
- Blocks: PNR-28

---

### PNR-25: Suspend and revoke NANNM ID

**Type:** Feature
**Jira Type:** Story
**Priority:** High
**Complexity:** Small
**Phase:** Day 3
**Labels:** `backend`, `admin`, `workflow`
**PRD Reference:** Sections 5 (US-07), 7.2, 15.2

#### Description

As a supervisor, I want to suspend or revoke a NANNM ID with a reason, so that suspected impersonation or fake licences are contained.

#### Acceptance Criteria

- [ ] Given an approved nurse, when a supervisor suspends with a reason, then the record becomes `suspended`.
- [ ] Given an approved or suspended nurse, when a supervisor revokes with a reason, then the record becomes `revoked`.
- [ ] Given a revoked nurse, when the public page is opened, then "Revoked" is shown.
- [ ] Given a suspended nurse, when a supervisor reinstates, then the record returns to `approved`.
- [ ] Given a revoked nurse, when any transition is attempted, then it is blocked.
- [ ] Given each action, when the audit log is viewed, then the actor, reason, and timestamp are recorded.

#### Technical Notes

- Files: `registry/admin.py`, `registry/services.py`, `registry/tests.py`.
- Enforce transitions in `services.py`.
- Require a reason for suspend and revoke.
- Do not delete records.

#### Dependencies

- Blocked by: PNR-11, PNR-12
- Blocks: PNR-26, PNR-28

---

## Day 4: Demo Polish and Handoff

### PNR-26: Demo script, README, backup and reset

**Type:** Technical
**Jira Type:** Task
**Priority:** High
**Complexity:** Small
**Phase:** Day 4
**Labels:** `docs`, `demo`
**PRD Reference:** Sections 11, 12, 15.4

#### Description

As a presenter, I want a README and demo script, so that another person can run the demo from scratch without help.

#### Acceptance Criteria

- [ ] Given a clean clone, when following the README, then setup takes under 15 minutes.
- [ ] Given the README, when read, then it lists install, migrate, seed, run, and login credentials.
- [ ] Given the demo script, when followed, then it covers registration through export in 10 steps.
- [ ] Given the database and media, when backup commands are run, then both are copied.
- [ ] Given a reset is needed, when the reset command is run, then the demo can be reseeded.

#### Technical Notes

- Files: `README.md`, `docs/demo-script.md`.
- Include exact commands and expected results.
- Include backup and restore commands for SQLite and media.
- State clearly that the data is fake.

#### Dependencies

- Blocked by: PNR-11 through PNR-25
- Blocks: PNR-27, PNR-29

---

### PNR-27: Demo data polish and demo-mode banner

**Type:** Technical
**Jira Type:** Task
**Priority:** Low
**Complexity:** Small
**Phase:** Day 4
**Labels:** `demo`, `frontend`
**PRD Reference:** Sections 7.9, 11

#### Description

As a presenter, I want realistic seeded data and a visible demo banner, so that the demo looks credible and nobody mistakes fake records for real ones.

#### Acceptance Criteria

- [ ] Given the seeded data, when viewed, then names, employers, LGAs, wards, and cadres look realistic.
- [ ] Given the app, when opened in demo mode, then a banner states that data is fake.
- [ ] Given empty lists, when viewed, then a helpful empty state is shown.
- [ ] Given an invalid form, when submitted, then the error names the field and the fix.
- [ ] Given a phone-sized screen, when using registration and verification, then the layout is usable.

#### Technical Notes

- Files: `registry/management/commands/seed_demo.py`, `templates/base.html`, `static/css/app.css`.
- Use a `DEMO_MODE` setting for the banner.
- No lorem ipsum; use plausible Nigerian names and Plateau employers.
- Keep CSS small; no framework.

#### Dependencies

- Blocked by: PNR-10, PNR-26
- Blocks: none

---

### PNR-28: Smoke test suite and bug-fix pass

**Type:** Technical
**Jira Type:** Task
**Priority:** High
**Complexity:** Medium
**Phase:** Day 4
**Labels:** `backend`, `tests`
**PRD Reference:** Sections 11, 12

#### Description

As a developer, I want smoke tests covering the demo path, so that Day 4 changes do not break the flows that matter.

#### Acceptance Criteria

- [ ] Given the test suite, when run, then it covers registration, approval, public verification, HR scoping, renewal, reminders, audit, and CSV export.
- [ ] Given the test suite, when run, then all tests pass.
- [ ] Given the demo script, when executed, then no page returns a 500.
- [ ] Given a permission regression, when tests run, then the failing case is caught.
- [ ] Given the final build, when lint runs, then there are no blocking errors.

#### Technical Notes

- Files: `registry/tests.py`, `api/tests.py`.
- Use Django's built-in test runner; no pytest dependency.
- Keep tests fast and database-isolated.
- Fix bugs only; no new features on Day 4.

#### Dependencies

- Blocked by: PNR-11 through PNR-25
- Blocks: none

---

### PNR-29: Optional VPS deployment configuration

**Type:** Technical
**Jira Type:** Task
**Priority:** Low
**Complexity:** Medium
**Phase:** Day 4 (stretch)
**Labels:** `deploy`, `ops`
**PRD Reference:** Sections 8, 9

#### Description

As a system owner, I want a documented VPS deployment path, so that the app can run after the event without a rewrite.

#### Acceptance Criteria

- [ ] Given a VPS with Python, when following the deploy notes, then Gunicorn and WhiteNoise serve the app.
- [ ] Given `DATABASE_URL`, when the app starts, then it uses PostgreSQL.
- [ ] Given `collectstatic`, when run, then static files are served.
- [ ] Given cron, when configured, then the reminder command runs daily.
- [ ] Given a domain, when TLS is configured, then the app is reachable over HTTPS.

#### Technical Notes

- Files: `README.md`, `deploy/`, `.env.example`.
- No Docker requirement; document a plain systemd service.
- Keep this stretch-only; the laptop demo takes priority.

#### Dependencies

- Blocked by: PNR-26
- Blocks: none

---

### PNR-30: Thin API for core records

**Type:** Technical
**Jira Type:** Task
**Priority:** Medium
**Complexity:** Medium
**Phase:** Day 4
**Labels:** `backend`, `api`
**PRD Reference:** Sections 10, 13

#### Description

As a frontend developer, I want versioned API endpoints for registration, verification, and licences, so that the Jinja frontend can later be replaced with a Vite app without changing the backend.

#### Acceptance Criteria

- [ ] Given valid credentials, when calling `/api/v1/auth/token/`, then a DRF token is returned.
- [ ] Given an officer token, when listing or creating nurses, then permissions match the web app.
- [ ] Given an officer token, when uploading a licence, then the document is stored and linked.
- [ ] Given a supervisor token, when approving a licence, then the renewal updates the nurse.
- [ ] Given a public request, when verifying a NANNM ID, then the minimal public response is returned.
- [ ] Given an HR token, when requesting another employer's nurse, then access is denied.

#### Technical Notes

- Files: `api/serializers.py`, `api/views.py`, `api/urls.py`.
- Use DRF `TokenAuthentication`; no JWT package.
- Reuse services from the web views; do not duplicate business logic.
- Document endpoints in the README; no OpenAPI dependency for MVP.

#### Dependencies

- Blocked by: PNR-02, PNR-12, PNR-15, PNR-19
- Blocks: none

---

## Dependency Graph

```
PNR-01
  └── PNR-02
        ├── PNR-03 ──> PNR-07
        ├── PNR-04 ──> PNR-11, PNR-17, PNR-23, PNR-24
        ├── PNR-05 ──> PNR-07, PNR-11, PNR-17, PNR-25
        ├── PNR-06 ──> PNR-07, PNR-08, PNR-13
        ├── PNR-12 ──> PNR-11, PNR-13, PNR-15, PNR-25, PNR-30
        └── PNR-20 ──> PNR-21
PNR-07 ──> PNR-08, PNR-09
PNR-08 ──> PNR-11, PNR-13
PNR-10 ──> PNR-26, PNR-27
PNR-11 ──> PNR-19, PNR-25, PNR-26
PNR-13 ──> PNR-14
PNR-15 ──> PNR-16, PNR-30
PNR-17 ──> PNR-18
PNR-22 ──> PNR-21
PNR-23 ──> PNR-24
PNR-26 ──> PNR-27, PNR-29
```

No circular dependencies. Every story is reviewable and mergeable on its own.

---

## Traceability to PRD

| PRD Section | Stories |
|---|---|
| 4. In Scope: registration | PNR-07, PNR-08, PNR-09 |
| 4. In Scope: review and approval | PNR-11, PNR-12 |
| 4. In Scope: card and QR | PNR-13, PNR-14 |
| 4. In Scope: public verification | PNR-15, PNR-16 |
| 4. In Scope: HR portal | PNR-17, PNR-18 |
| 4. In Scope: expiry and reminders | PNR-20, PNR-21, PNR-22 |
| 4. In Scope: renewal | PNR-19 |
| 4. In Scope: suspend and revoke | PNR-25 |
| 4. In Scope: audit and export | PNR-23, PNR-24 |
| 4. In Scope: seed data | PNR-10, PNR-27 |
| 4. In Scope: API | PNR-30 |
| 6. Architecture | PNR-01, PNR-02, PNR-06 |
| 9. Security | PNR-03, PNR-05, PNR-06, PNR-16, PNR-23 |
| 11. Success criteria | PNR-26, PNR-28 |
| 12. Phases | All stories grouped by Day |
| 15. Data model | PNR-02, PNR-03, PNR-20 |

---

## Definition of Done

A story is done when:

- [ ] Code is merged to the main branch.
- [ ] Migrations are included and apply cleanly.
- [ ] Permissions match the PRD exposure table.
- [ ] No secrets, real NINs, or real nurse data are committed.
- [ ] Acceptance criteria are met and demonstrated.
- [ ] Relevant tests pass with `python manage.py test`.
- [ ] Audit coverage is present for privileged actions.
- [ ] The demo path still works end to end.
- [ ] README or demo script is updated when behavior changes.

---

## Cut Order If Time Slips

Cut from the bottom, never from the top:

1. PNR-29 (VPS deploy) — stretch only.
2. PNR-27 (demo polish) — nice to have.
3. PNR-30 (thin API) — defer if the demo is at risk.
4. PNR-09 (duplicate warning) — manual check is acceptable.
5. PNR-18 (employment confirmation) — HR view still works.
6. PNR-24 (CSV export) — show admin list instead.

**Never cut:** PNR-07, PNR-08, PNR-11, PNR-12, PNR-15, PNR-26, PNR-28.
