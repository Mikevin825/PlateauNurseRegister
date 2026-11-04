# Plan: Frontend UI and Registration Flow Remediation

## Summary

Fix the login field styling shown in the supplied screenshot, replace the long nurse registration page with a short accessible step-by-step flow, and close the highest-impact frontend/backend gaps found in the cross-repository audit. Preserve the current clinical visual language, role rules, registration API contract, and existing React routes. Do not store NIN, passwords, or uploaded documents in browser storage.

## User Story

As a nurse, hospital HR user, registry supervisor, or super admin,
I want clear, responsive screens whose controls work with the connected API,
So that I can register, sign in, review records, and manage my account without confusing layout or misleading controls.

## Metadata

| Field | Value |
|---|---|
| Type | BUG_FIX / ENHANCEMENT |
| Complexity | HIGH |
| Systems Affected | React Vite UI, Django REST API, Django configuration, auth and file access, deployment routing |
| Jira Issue | N/A |

---

## Audit Findings to Resolve

1. The shared `clinical-ui.css` form-control selector applies a border to `.form-group input`, overriding the borderless input inside `.input-wrapper`. The input gets a second outline inside the wrapper, as shown in the login screenshot.
2. Nurse registration currently renders personal details, professional details, employment, uploads, and consent in one long page.
3. Django CORS advertises only `GET, POST, OPTIONS`, while admin CRUD uses `PATCH` and `DELETE`.
4. HR registration approval only adds the HR group when it already exists; a clean database can approve an HR request without granting the HR role.
5. Admin nurse API responses expose direct media URLs for licence scans, while an existing Django session-protected document view is not usable by the token-authenticated React client.
6. HR Reports uses synthetic nurse records and HR Settings displays hard-coded account/institution data and non-persisting controls.
7. The backend permits nurse review actions that the UI does not expose; suspended records have no UI reinstate action, and revoked records are terminal by backend policy.
8. The nurse profile has a photo-change button without a handler or supporting nurse photo-update API.
9. Login currently has no password reset/change route, and signing out removes only the browser token; it does not revoke the API token.
10. Deployment configuration does not define how Vite's built SPA, Django HTML routes, `/api/v1/`, Django `/admin/`, and React `/admin/...` paths are dispatched in production.
11. Public verification's example ID (`PSNR-2026-00001`) conflicts with backend-issued `PLT-NUR-000001` format.
12. Admin and HR record dialogs need complete keyboard focus behavior. HR directory and Employment Verification also duplicate the employment confirmation action.
13. Verification results currently render after the page content; users can have to scroll away from the lookup controls to see results or continue.

---

## Patterns and Contracts to Preserve

### Login fields and validation

`src/pages/NurseLogin.jsx` and `src/pages/HospitalLogin.jsx` use labeled email/password fields, a password visibility control, a busy submit state, API error messages, and role-based redirects. Keep those interactions and tune the shared wrapper/input cascade rather than rebuilding authentication.

### Nurse registration payload

`registry/forms.py::NurseRegistrationForm` is the authoritative registration contract. Submit multipart fields named `full_name`, `email`, `phone`, `nin`, `password`, `licence_number`, `licence_expiry`, `specialty`, `cadre`, `employer` or `custom_employer_name`, `ward`, `licence_scan`, `selfie`, `consent`, and `confirm_duplicate` as appropriate.

`src/apiService.jsx::registerNurse` already handles a `FormData` body. Keep one final request after all steps; do not upload documents on step navigation.

### Error and status handling

Keep entered form values after validation failures. Map backend field errors to the relevant step and control; when an error occurs on another step, navigate to that step and focus an error summary. GOV.UK guidance recommends an error summary linked to each errored answer and focus moved to the summary; W3C requires status changes to be programmatically announced.

References: [GOV.UK multi-page question pages](https://design-system.service.gov.uk/patterns/question-pages/), [GOV.UK error summary](https://design-system.service.gov.uk/components/error-summary/), [WCAG status messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html).

For the verification result dialog, follow the [WAI-ARIA APG modal dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/): move focus into the dialog, keep keyboard focus within it while open, close on Escape, provide a visible close button, make the background inert, and return focus to the lookup control when closed.

---

## Proposed Registration Flow

Use a four-step wizard with one focused panel visible at a time. Show a labeled progress indicator (step number, title, and total), Back and Continue controls, and retain state in component memory only.

1. **Personal and account details** — legal name, email, phone, NIN, password, password confirmation.
2. **Professional credentials** — licence number, expiry, cadre, specialty.
3. **Employment** — approved employer selector, conditional custom-employer field, ward/unit.
4. **Documents, consent, and review** — licence scan, selfie, required consent, conditional duplicate confirmation, concise review summary, and final submit.

Validate only the current step on Continue. On final submit, construct the exact multipart payload expected by `NurseRegistrationForm`, display inline errors and a step-level summary, preserve values on failure, prevent double submission, and route successful registration through the existing nurse account flow.

---

## Files to Change

| File | Action | Purpose |
|---|---|---|
| `plateau-nurse-registry/src/clinical-ui.css` | UPDATE | Stop shared input styles from adding a second border inside auth input wrappers; refine shared focus states. |
| `plateau-nurse-registry/src/pages/NurseLogin.css` | UPDATE | Keep wrapper as the single visible control surface and normalize icon/input sizing. |
| `plateau-nurse-registry/src/pages/HospitalLogin.css` | UPDATE | Ensure HR login uses the same single-border field treatment. |
| `plateau-nurse-registry/src/pages/NurseRegister.jsx` | UPDATE | Implement the four-step registration flow, state preservation, step validation, review, and backend error mapping. |
| `plateau-nurse-registry/src/pages/NurseRegister.css` | UPDATE | Add responsive progress, step panel, error, and navigation styles. |
| `plateau-nurse-registry/src/pages/PublicVerify.jsx` | UPDATE | Correct the Registry ID example and show successful lookup results in an accessible modal without moving users to the bottom of the page. |
| `plateau-nurse-registry/src/pages/PublicVerify.css` | UPDATE | Style the verification result modal and narrow-screen full-height presentation. |
| `plateau-nurse-registry/src/pages/NurseProfile.jsx` | UPDATE | Remove the inert photo-change control or wire it to the implemented photo flow. |
| `plateau-nurse-registry/src/pages/hr/HRReports.jsx` | UPDATE | Replace synthetic rows with employer-scoped API results or remove unsupported export/report controls until API exists. |
| `plateau-nurse-registry/src/pages/hr/HRSettings.jsx` | UPDATE | Replace hard-coded profile/preferences and fake password success with real API-backed settings or accurately mark unsupported capabilities unavailable. |
| `plateau-nurse-registry/src/pages/admin/AdminNurses.jsx` | UPDATE | Align visible actions with backend allowed transitions; support reasons and confirmation consistently. |
| `plateau-nurse-registry/src/pages/admin/AdminRecords.css` | UPDATE | Complete responsive and focus behavior for admin dialogs. |
| `plateau-nurse-registry/src/pages/hr/HRNurseDirectory.jsx` | UPDATE | Coordinate employment confirmation placement with the standalone Employment Verification page; add dialog focus management. |
| `plateau-nurse-registry/src/pages/hr/HRNurseDirectory.css` | UPDATE | Complete dialog keyboard/focus and mobile behavior. |
| `plateau-nurse-registry/src/components/nurse/NurseLayout.jsx` | UPDATE | Add an accessible skip link if there is no shared app-level implementation; route sign-out through token revocation once available. |
| `plateau-nurse-registry/src/components/hr/HRLayout.jsx` | UPDATE | Same shared skip-link and sign-out integration. |
| `plateau-nurse-registry/src/components/admin/AdminLayout.jsx` | UPDATE | Same shared skip-link and sign-out integration. |
| `plateau-nurse-registry/src/apiService.jsx` | UPDATE | Add APIs for private file retrieval, HR reports/settings, password changes, and logout only where the backend support is added; remove or correct `getNurseById`. |
| `Silicon Plateau/api/middleware.py` | UPDATE | Advertise and validate the HTTP methods used by the frontend, including `PATCH` and `DELETE`, for configured origins. |
| `Silicon Plateau/api/views.py` | UPDATE | Ensure HR role group exists during HR approval; add private document/photo and missing workflow endpoints; add login abuse throttling; align review actions. |
| `Silicon Plateau/api/urls.py` | UPDATE | Expose only the new API endpoints needed by the React UI. |
| `Silicon Plateau/registry/views.py` | UPDATE | Reuse access rules for private media delivery without requiring a Django session for React token-authenticated users. |
| `Silicon Plateau/config/settings.py` | UPDATE | Make release checks fail safely for missing production secrets and define production HTTPS/security settings through environment configuration. |
| `Silicon Plateau/.env.example` | UPDATE | Keep development defaults clearly local-only and document required production variables. |
| Deployment/reverse-proxy configuration | CREATE / UPDATE | Serve Vite `dist`, provide SPA fallback, forward `/api/v1/`, and avoid Django/React admin route collisions. Choose the actual host before implementation. |
| `Silicon Plateau/api/tests.py` | UPDATE | Cover CORS preflight methods, fresh-database HR group assignment, role access, token-protected documents, throttling, and new API contracts. |
| `plateau-nurse-registry` UI tests / browser smoke flows | CREATE / UPDATE | Cover the four-step wizard, field/server errors, uploads, responsiveness, and login field visuals. |

---

## Tasks

### Task 1: Fix login field surfaces

- **Files**: `src/clinical-ui.css`, `src/pages/NurseLogin.css`, `src/pages/HospitalLogin.css`
- **Implement**: Scope the shared bordered input selector so it does not style nested `.input-wrapper input`; retain a single border on `.input-wrapper`; keep the existing focus-within ring; prevent icons and password toggle from shrinking; verify email/password text has consistent vertical alignment.
- **Validate**: Compare both nurse and staff login fields to the screenshot at desktop and narrow viewport sizes; verify keyboard focus remains visible and input focus does not show a second border.

### Task 2: Build the nurse registration wizard

- **Files**: `src/pages/NurseRegister.jsx`, `src/pages/NurseRegister.css`
- **Implement**: Four steps as listed above; back/continue; per-step validation; progress semantics; conditionally show custom employer and duplicate confirmation; final review; preserve `File` values between steps; final multipart submit using current backend field names.
- **Mirror**: `registry/forms.py::NurseRegistrationForm`, `api/views.py::register_nurse`, and current `registerNurse(FormData)` helper.
- **Validate**: Ensure no step navigation submits early; invalid step focuses an error summary; backend field errors return to the right step; valid submit creates one pending nurse registration and successful account redirect.

### Task 3: Improve form accessibility and responsive behavior

- **Files**: `NurseRegister.jsx`, `NurseRegister.css`, login forms, app layouts, admin/HR dialog components and styles.
- **Implement**: Real step headings and progress labels; link summary errors to fields; announce upload, validation, and submission status; focus first invalid field/error summary; add dialog focus trap, Escape handling and focus return; add skip-to-content links; ensure controls remain usable at 320px width and with touch/keyboard.
- **Validate**: Keyboard-only pass, screen-reader announcement check, 320px/390px/tablet/desktop viewport pass, and reduced-motion pass.

### Task 4: Align small UI details and nurse review actions

- **Files**: `PublicVerify.jsx`, `PublicVerify.css`, `NurseProfile.jsx`, `AdminNurses.jsx`, API service.
- **Implement**: Use `PLT-NUR-000001` in the public search example. On successful `/verify` lookup, open the nurse result in a polished modal centered over the current page so users do not have to scroll to find the result or another action. Include a prominent close button, nurse photo when available, Registry ID, name, employer, licence status and expiry, and a clear status treatment. Keep not-found/network errors adjacent to the search form instead of hiding them below the page. At small widths, make the dialog a comfortable full-screen sheet with a visible close control and only internal scrolling if content exceeds the viewport. Implement focus placement, a contained tab sequence, Escape close, background inertness, and focus return to the search submit control. Also remove or implement the profile camera button; add only status actions permitted by backend transition rules; support reason entry for transitions requiring reasons; make revoked status explicitly terminal; replace `prompt()` review reason capture with an accessible inline dialog.
- **Validate**: Confirm every displayed control has an action and every available API action is either intentionally omitted with a documented reason or reachable in the UI.

### Task 5: Replace fabricated HR report/settings behavior

- **Files**: HR Reports, HR Settings, API client, backend API/views/URLs.
- **Implement**: Build an employer-scoped report endpoint if exports remain in scope; load profile/employer info from `/me/` and backend employer data; persist preferences only after adding a data model/API; add a secure password-change endpoint or remove the nonfunctional form and provide a clear account recovery route. Do not display sample people or local-only success as saved data.
- **Validate**: Verify records and counts are scoped to the HR user’s employer, empty states are accurate, filters/export use live records, and settings survive reload only when persisted by the backend.

### Task 6: Fix cross-origin CRUD and HR role provisioning

- **Files**: `api/middleware.py`, `api/views.py`, `api/tests.py`.
- **Implement**: Allow only configured origins while including the actual frontend methods and headers; create or retrieve the HR group before assigning a newly approved HR account. Keep authorization checks in API views; frontend route guards are not an authorization boundary.
- **Validate**: Exercise preflight for `PATCH` and `DELETE`; approve an HR request with no pre-created groups and verify the resulting `/me/` role is `hr` and HR route access works.

### Task 7: Secure private media and add auth lifecycle endpoints

- **Files**: `api/views.py`, `api/urls.py`, `registry/views.py`, `apiService.jsx`, auth layouts, API tests.
- **Implement**: Stop returning unrestricted document URLs. Provide a token-authenticated private document response or short-lived signed download URL with checks for staff reviewer authorization. Add login throttling, password change/recovery as agreed, and logout token revocation; use the appropriate production HTTPS-only configuration.
- **Validate**: Anonymous, unrelated HR, and unauthorized roles cannot fetch private files; authorized reviewers can; logout revokes token; repeated failed login attempts are limited; passwords never enter browser storage or logs.

### Task 8: Define production frontend/backend routing

- **Files**: deployment configuration and project README/environment examples.
- **Implement**: Choose one deployment topology and configure it explicitly: serve the Vite `dist` SPA with a fallback for React paths, proxy `/api/v1/` to Django, and disambiguate React `/admin/...` from Django admin `/admin/`. Set production API base, allowed hosts, CORS origins, HTTPS, secret, media storage, and debug values from production environment variables.
- **Validate**: Test deep links including `/nurse/register`, `/hr/settings`, and `/admin/login` on the built deployment; verify API CORS and uploads from the deployed frontend origin.

### Task 9: Remove dead helpers and obsolete placeholders

- **Files**: `apiService.jsx`, `HRSectionPlaceholder.jsx`, other unreferenced components.
- **Implement**: Correct or remove `getNurseById` because the ID argument is ignored and no detail route exists; remove obsolete placeholder components that are no longer routed, or document their intended use.
- **Validate**: Search imports/exports and confirm there are no dead controls, fake data, or API helpers whose signature differs from their endpoint.

---

## Risks and Decisions

| Risk / decision | Mitigation |
|---|---|
| The real production host and same-origin/proxy setup are not specified. | Resolve the deployment topology before merging routing/config changes; keep Vite dev proxy behavior distinct from production routing. |
| Multi-step registration includes NIN and files. | Keep sensitive values and `File` objects in memory only; don't use local storage or session storage; make refresh behavior explicit if state is lost. |
| A result dialog can obscure or trap content if implemented with ARIA alone. | Use native `<dialog>` or fully implement modal behavior; follow the WAI-ARIA APG modal pattern for focus, keyboard containment, Escape, close control, inert background, and focus return. |
| Backend duplicate detection is server-side and can return an error at final submit. | Preserve every step and entered value, route the user to consent/duplicate confirmation, and retry only after explicit confirmation. |
| Current media URLs may be served by an external private storage provider in production. | Confirm the storage ACL before replacing URL delivery; require authorization regardless of storage provider. |
| HR settings scope could expand beyond password change/preferences. | Implement only fields backed by a persisted model and API; keep unsupported controls out of the live UI. |

---

## Validation

```bash
# Frontend static checks
cd /home/albasheer/Desktop/plateau-nurse-registry
npm run build
npm run lint

# Backend checks and API tests
cd "/home/albasheer/Desktop/Silicon Plateau"
.venv/bin/python manage.py check
.venv/bin/python manage.py test api
.venv/bin/python manage.py check --deploy  # using production-like environment variables
```

Also run browser checks at mobile/tablet/desktop widths, keyboard-only registration, screen-reader status announcements, actual login/registration against the backend, CORS preflight for `PATCH`/`DELETE`, and private file authorization. Do not treat Vite development proxy success as production CORS verification.

---

## Acceptance Criteria

- [ ] Nurse, HR, and staff login fields show one clean border per control with a visible focus state.
- [ ] Nurse registration is a four-step flow with visible progress, Back/Continue, step validation, preserved values, and final review.
- [ ] A successful public nurse lookup opens results in a clear modal from the current viewport; the user does not need to scroll to the page bottom to see the result or close it.
- [ ] Verification modal is usable on narrow screens, has a visible close control, supports Escape and keyboard focus containment, and returns focus to the lookup action when closed.
- [ ] Registration submits the exact backend multipart contract, including conditional custom employer, consent, duplicate confirmation, scan, and selfie.
- [ ] Errors are actionable, associated with fields, announced to assistive technology, and do not clear entered data.
- [ ] Mobile, keyboard, and reduced-motion behavior are reviewed at target viewports.
- [ ] React HR reports/settings contain no fabricated records or success claims for unpersisted changes.
- [ ] Every visible UI action has a working API or is removed/clearly unavailable.
- [ ] Fresh database HR approval assigns the HR role correctly.
- [ ] Configured cross-origin React clients can use the required HTTP methods; unconfigured origins remain denied.
- [ ] Private nurse documents require authenticated, role-checked access.
- [ ] Auth logout/recovery behavior is explicit and security-reviewed.
- [ ] Production routing serves Vite deep links and routes API/admin requests to the correct application.
- [ ] Frontend build/lint, backend API checks, API tests, and browser smoke flows pass.
