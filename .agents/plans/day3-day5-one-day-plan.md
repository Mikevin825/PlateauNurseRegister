# Plan: Day 3–5 compressed into one delivery sprint

## Summary

This plan compresses the remaining Day 3–5 backlog into a single focused execution day. The goal is to ship the highest-value operational features without fragmenting the work: HR scoping, employment confirmation, status logic, expiry reminders, audit/export essentials, and demo handoff. Anything secondary or stretch (VPS, polished demo mode, broader API expansion) is explicitly deferred unless time remains at the end.

## User Story

As a registry operator or HR user,
I want the core operational workflows to be working end-to-end,
so that the system can be demonstrated and used in a single-day delivery window.

## Metadata

| Field | Value |
|-------|-------|
| Type | ENHANCEMENT / TECHNICAL DELIVERY |
| Complexity | MEDIUM |
| Systems Affected | `registry/`, `config/`, `templates/`, `static/`, `README.md` |
| Jira Issue | N/A |

---

## Must-do vs defer

### Must ship in one day
- PNR-17: HR employer-scoped admin view
- PNR-18: Employment confirmation action
- PNR-20: Licence status computation and filters
- PNR-21: Expiry reminder command with dedupe
- PNR-22: SMTP configuration and expiry email
- PNR-23: Audit logging and admin viewer
- PNR-24: CSV export admin action
- PNR-25: Suspend and revoke NANNM ID
- PNR-26: Demo script, README, backup and reset
- PNR-28: Smoke test suite and bug-fix pass

### Defer if time is short
- PNR-19: Renewal upload and approval
- PNR-27: Demo data polish and demo-mode banner
- PNR-29: Optional VPS deployment configuration
- PNR-30: Thin API for core records

This keeps the app demo-ready while respecting the one-day constraint.

---

## Patterns to Follow

### Naming
```python
# SOURCE: registry/permissions.py:1-74
OFFICER = "Officer"
HR = "HR"

def nurses_for_user(user):
    if is_super_admin(user) or is_supervisor(user) or is_officer(user):
        return Nurse.objects.all()
    if is_hr(user):
        return Nurse.objects.filter(employer__hr_users=user).distinct()
    return Nurse.objects.none()
```

### Error Handling
```python
# SOURCE: registry/services.py:7-31, 76-104
if not can_reveal_nin(actor):
    raise PermissionDenied("You do not have permission to reveal this NIN.")

if new_status not in ALLOWED_TRANSITIONS.get(old_status, set()):
    raise ValidationError(f"Invalid transition from {old_status} to {new_status}.")
```

### Tests
```python
# SOURCE: registry/tests.py:512-596
class AdminTests(RegistryTestBase):
    def test_superuser_can_open_admin_and_models_are_registered(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)
```

---

## Files to Change

| File | Action | Purpose |
|------|--------|---------|
| `registry/admin.py` | UPDATE | HR scoping, read-only admin, export action, confirmation hooks |
| `registry/services.py` | UPDATE | Employment confirmation, suspend/revoke transitions, reminder logic support |
| `registry/models.py` | UPDATE | Status computation, reminder notification fields, audit-friendly helpers |
| `registry/permissions.py` | UPDATE | Employer-scoped checks and access patterns |
| `registry/tests.py` | UPDATE | Cover HR, status, reminder, audit, export and security flows |
| `config/settings.py` | UPDATE | SMTP defaults, reminder window configuration |
| `README.md` | UPDATE | Demo setup, reset and backup instructions |
| `templates/email/expiry_reminder.txt` | CREATE | Plain-text reminder email |
| `registry/management/commands/send_expiry_reminders.py` | CREATE | Reminder command implementation |
| `registry/management/commands/seed_demo.py` | UPDATE | Demo data and reset flows |

---

## Execution Strategy

### Task 1: HR scope + confirm employment (Priority 1)
- **Files**: `registry/admin.py`, `registry/permissions.py`, `registry/services.py`
- **Action**: UPDATE
- **Implement**:
  - HR users only see `Nurse` records for their employer.
  - HR cannot change nurses; all fields remain read-only.
  - Add a service to confirm employment and timestamp `employer_confirmed_at` / `employer_confirmed_by`.
  - Deny access when a nurse belongs to another employer.
- **Mirror**: `registry/permissions.py:1-74`, `registry/tests.py:276-291`
- **Validate**: `python manage.py test registry.tests.AdminTests`

### Task 2: Status rules and filtering (Priority 1)
- **Files**: `registry/models.py`, `registry/admin.py`, `registry/tests.py`
- **Action**: UPDATE
- **Implement**:
  - Add a licence status property that distinguishes green/yellow/red/grey/black based on expiry and record state.
  - Keep thresholds explicit in settings and test the 180-day boundary.
  - Expose filter logic in the admin list.
- **Mirror**: `registry/models.py:100-128`
- **Validate**: `python manage.py test registry.tests` (or targeted status tests)

### Task 3: Reminder system + SMTP config (Priority 1)
- **Files**: `config/settings.py`, `registry/models.py`, `registry/management/commands/send_expiry_reminders.py`, `templates/email/expiry_reminder.txt`, `registry/tests.py`
- **Action**: CREATE / UPDATE
- **Implement**:
  - Add SMTP configuration with console fallback in local dev.
  - Create reminder command that sends exactly one email per `(nurse, expiry)`.
  - Record failed notifications rather than crashing the run.
  - Use the existing `Notification` model and unique constraint pattern.
- **Mirror**: `registry/models.py:171-264`, `registry/services.py:115-147`
- **Validate**: targeted reminder tests + `python manage.py test`

### Task 4: Audit + export (Priority 2)
- **Files**: `registry/admin.py`, `config/settings.py`, `registry/tests.py`
- **Action**: UPDATE
- **Implement**:
  - Validate audit log registration remains active for key models.
  - Add CSV export action for super admin only.
  - Ensure export includes the fixed column set without NIN.
  - Keep the action accessible only to the right role.
- **Mirror**: `registry/apps.py:8-16`, `registry/admin.py:1-117`
- **Validate**: `python manage.py test registry.tests.AdminTests`

### Task 5: Suspend/revoke workflow and transition hardening (Priority 2)
- **Files**: `registry/services.py`, `registry/admin.py`, `registry/tests.py`
- **Action**: UPDATE
- **Implement**:
  - Extend allowed transitions to include suspend/revoke and required reasons.
  - Block invalid transitions and blocked reactivation rules.
  - Add public-facing status behavior already supported by `public_licence_status`.
- **Mirror**: `registry/services.py:20-104`
- **Validate**: targeted transition tests

### Task 6: Demo handoff + smoke tests (Priority 1)
- **Files**: `README.md`, `registry/management/commands/seed_demo.py`, `registry/tests.py`
- **Action**: UPDATE
- **Implement**:
  - Add clear setup, migrate, seed, run, and reset instructions.
  - Document admin credentials and demo flow.
  - Add a smoke-test pass to cover public verification, approval, HR access, and reminder path.
- **Mirror**: `registry/tests.py:512-614`
- **Validate**: full `python manage.py test`

---

## Validation

Run these in order, and stop once they pass:

```bash
python manage.py test registry.tests.AdminTests
python manage.py test registry.tests
python manage.py check
```

If time remains after all must-have tasks:

```bash
python manage.py test
```

---

## Acceptance Criteria

- [ ] HR scope is enforced in admin and URL access paths.
- [ ] Employment confirmation updates timestamp and actor.
- [ ] Licence status rules match the green/yellow/red/grey/black thresholds.
- [ ] Reminder emails are deduplicated and failure-safe.
- [ ] SMTP config supports production and local console fallback.
- [ ] Audit log and CSV export are available to the right roles.
- [ ] Suspend/revoke transitions are enforced with reasons.
- [ ] README + reset flow make the project demoable from a clean checkout.
- [ ] Full test suite passes.

---

## One-day execution sequence

### Morning block (2–3 hours)
1. HR admin scope + read-only enforcement
2. Employment confirmation service + tests
3. Status calculation and filters

### Midday block (2–3 hours)
4. Reminder command + SMTP config
5. Audit/export coverage
6. Suspend/revoke transition update

### Final block (2 hours)
7. Demo instructions, reset path, smoke tests
8. Final test pass and cleanup

## Deferred if needed
- PNR-19 renewal flow
- PNR-27 demo polish
- PNR-29 VPS deploy
- PNR-30 API

These can be shipped after the demo or in a second pass without risking the core registry functionality.
