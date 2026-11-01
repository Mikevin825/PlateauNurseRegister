# Plateau State Nurse Registry and Licence Verification Platform: MVP Spec

Status: draft from interview, 31 Oct 2026
Success measure: selection or adoption (workshop judges or the council choose it)
Timeline: full MVP in a few weeks

## 1. Problem

The Plateau State office lost its devices and paper records in an armed robbery. There is no register of nurses in the state. They need a digital register that survives theft and disasters, shows who is licensed, tracks expiry, flags fake or impersonating nurses, and lets hospital HR check a nurse quickly.

## 2. Who owns it (needs confirmation)

- Client contact represents the NANNM Plateau chapter (the nurses' association/union).
- The licensing regulator is the Nursing and Midwifery Council of Nigeria (NMCN), a federal body. NANNM does not issue licences.
- Open: what authority NANNM has to act on expired or fake licences. Not decided. Until clarified, the platform flags and notifies, and any enforcement step is a manual decision by an admin.
- Open: who is the legal data controller under the NDPA (NANNM, NMCN, or a state body). Resolve before launch.

## 3. Key facts and confidence

- No public NMCN verification API was found. NMCN's own verification flow is an application with a fee, aimed at foreign boards. Confidence: moderate. Confirm directly with NMCN.
- Licence validity period is unconfirmed. The system must not hardcode 3 years. It uses the expiry date printed on each licence.
- NMCN's portal was closed in Dec 2023 and reopened in Sep 2024, so do not depend on it.

## 4. Decisions made

| Area | Decision |
|---|---|
| Licence check | Officer verifies manually against the uploaded scan and NMCN records |
| Scale | 5,000 to 20,000 nurses at launch |
| Onboarding | Ward-by-ward drives by officers |
| Offline | Offline-capable PWA for registration, sync when online |
| Identity proof | Live selfie match, NIN capture, in-person visit with originals, employer confirmation |
| Profile fields | Name, photo, NIN, licence number, licence expiry, current employer and ward, specialty/cadre |
| HR access | Public basic lookup, login for detail |
| Reminders | Email only |
| Expired licence | Auto notify nurse and employer, flag red, public status shows expired |
| Renewal | Track only. Nurse renews with NMCN, then uploads the new licence for approval |
| ID card | Digital first (QR), optional printed card |
| Hosting | Cloud, single region, with scheduled backups |
| Admin roles | Three tiers (officer, supervisor, super admin) with full audit log |
| Consent | Checkbox at registration |
| Stack | Django + PostgreSQL + Django REST Framework, PWA front end by teammate (see section 5) |

## 5. Stack (decided)

- Backend: Django with PostgreSQL and Django REST Framework. Chosen over Flask because the project is data-heavy and admin-heavy: Django's built-in admin, users, groups and permissions, ORM and migrations cover the review queue, three admin tiers and nurse list with little custom work. Both developers know Python.
- Audit log: django-simple-history or django-auditlog.
- Scheduled emails (90 days, 30 days, expiry): a management command run daily by cron for the MVP.
- Front end: PWA built by the front-end teammate against the REST API (framework to be confirmed, React or Next.js are fine). Offline registration uses an IndexedDB queue that syncs when online. This is the hardest part of the build, so assign it to whoever is stronger in JavaScript.
- Scope saver: officer review queue and super admin tools can run in Django's own admin. Custom screens are only needed for nurses, hospital HR and the public verify page.
- File storage: S3-compatible private bucket with signed URLs for licence scans and selfies.
- Hosting: a managed host or small VPS (for example Railway, Render or a VPS). Add a nightly encrypted export to a second provider, since a single region was chosen and the original problem was data loss.
- Email: a transactional email provider.
- Confidence: the framework choice is solid for this scope. Teammate's Django experience and front-end stack are unverified.

## 6. Users and roles

- Nurse: registers, uploads licence, views status, downloads ID card, uploads renewed licence.
- Officer: registers nurses on drives, reviews and approves applications, flags suspicious cases.
- Supervisor: resolves flagged cases, handles disputes, sends manual notices.
- Super admin: manages users and roles, exports data, views audit log, system settings.
- Hospital HR: approved hospital account, sees full verified profile of nurses in their hospital.
- Public: basic lookup by ID.

## 7. Core flows

1. Registration (nurse or officer on drive): consent checkbox, details, NIN, licence number and expiry, licence scan, live selfie, employer and ward. Status becomes Pending.
2. Review: officer compares scan, selfie and details, checks NMCN records, then Approves, Rejects with reason, or Flags. Approval issues a unique NANNM ID and QR card.
3. Employer confirmation: HR confirms the nurse works there. Stored as a confirmation flag with date.
4. Verification: anyone enters an ID or scans the QR. Public result shows name, photo, licence status, expiry date. Unknown ID shows "not registered". HR login shows employer, cadre and more detail.
5. Expiry handling: status computed from expiry date. Emails to nurse (and employer record) at 90 days, 30 days, and on expiry. Expired nurses show red on the dashboard and on the public page.
6. Renewal: nurse uploads the new licence, an officer approves, expiry updates, status returns to green.

## 8. Status colours

Computed from days to expiry, not stored:
- Green: more than 180 days
- Yellow: 180 days or fewer
- Red: expired
- Grey: pending review
- Black/flagged: suspected fake or impersonation (manual)

Thresholds are configurable by the super admin.

## 9. Admin dashboard

Totals by status, searchable and filterable nurse list (hospital, cadre, status, expiry window), review queue, flagged cases, expiring in 30/90 days, expired list with notice history, bulk export (CSV, super admin only), audit log viewer. Daily summary email to admins of newly expired nurses.

## 10. Data model (outline)

- users (id, role, email, status)
- nurses (id, nanm_id, full_name, nin_encrypted, photo_url, licence_number, licence_expiry, specialty, cadre, status, consent_at, created_by)
- licence_documents (id, nurse_id, file_url, uploaded_at, reviewed_by, decision, reason)
- employers (id, name, type, lga, contact_email, approved)
- employments (id, nurse_id, employer_id, ward, confirmed_at, current)
- notifications (id, nurse_id, employer_id, type, sent_at, status)
- audit_log (id, actor_id, action, entity, entity_id, timestamp, details)
- flags (id, nurse_id, reason, raised_by, resolved_by, resolved_at)

## 11. Privacy and security

- NDPA applies. Collect only fields listed above. NIN stored encrypted and never shown publicly or to HR.
- Public lookup returns minimal fields and is rate-limited with bot protection to stop bulk harvesting.
- Row-level security on all tables. Every officer action logged.
- Licence scans and selfies in a private bucket with signed URLs.
- Retention and deletion policy to be defined with the data controller.
- Offline PWA stores data locally in encrypted form and clears it after sync.

## 12. Risks

- Manual verification is slow at 5,000 to 20,000 records. Mitigate with bulk review tools and drive-time checks.
- Public lookup can be abused for scraping. Mitigate with rate limits and minimal output.
- Employer emails may be wrong or missing, so some notices will not land.
- Email-only reminders may be missed by nurses who rarely check email. SMS was not selected, so measure delivery and revisit.
- Unclear authority could stall enforcement even if the data is accurate.
