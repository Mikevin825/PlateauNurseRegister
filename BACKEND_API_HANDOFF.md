# Backend API Handoff Documentation

This document describes the current backend API surface used by the Plateau Nurse Registry application. It is intended as a developer handoff reference for frontend integration, QA, and future maintenance.

## Base URL

- Base URL: `/api/v1/`
- Example: `http://localhost:8000/api/v1/verify/PLT-NUR-000001/`

## Authentication

The API uses Django REST Framework token authentication.

- Header format: `Authorization: Token <token>`
- The app also accepts the `Bearer`-style token pattern in some frontend integrations, but the backend currently expects DRF token auth semantics.
- `token_login` returns a token in the response body.

### Common auth flow
1. `POST /api/v1/auth/token/` with `{ "email": "user@example.com", "password": "..." }`
2. Store the returned `token`
3. Include it in subsequent requests:
   - `Authorization: Token <token>`

---

## API Routes

### Public routes

#### `GET /api/v1/verify/<nanm_id>/`
Public nurse lookup for verification.

- Public access: yes
- Purpose: return public nurse verification payload
- Path param: `nanm_id`
- Response status: `200 OK`
- Error: `404 Not Found` when nurse is not found

Example response:

```json
{
  "nanm_id": "PLT-NUR-000001",
  "full_name": "Amina Musa",
  "photo_url": "http://localhost:8000/media/nurse_photos/....jpg",
  "licence_status": "Licensed",
  "licence_expiry": "2027-05-12",
  "employer": "Plateau Specialist Hospital",
  "record_status": "approved"
}
```

Notes:
- This is the main public verification endpoint.
- It returns only the public data contract, not private identifiers such as NIN.

---

### Authentication routes

#### `POST /api/v1/auth/token/`
Authenticate a user by email and password.

Request body:

```json
{
  "email": "user@example.com",
  "password": "StrongPass123!"
}
```

Success response:

```json
{
  "token": "abc123...",
  "access": "abc123..."
}
```

Possible errors:
- `400 Bad Request` when email/password is invalid

---

### Nurse self-service routes

#### `POST /api/v1/register/`
Create a nurse account and profile.

- Public access: yes
- Purpose: create a user + nurse profile in one action
- Validation: password must be at least 8 characters

Request body:

```json
{
  "email": "nurse@example.com",
  "password": "StrongPass123!",
  "full_name": "Grace Ibrahim",
  "phone": "08030000001",
  "licence_number": "PLT-LIC-00001",
  "licence_expiry": "2027-01-15",
  "specialty": "General Nursing",
  "cadre": "Nurse",
  "employer": 1,
  "ward": "Ward 1",
  "nin": "12345678901",
  "consent": true,
  "licence_scan": "<file>",
  "selfie": "<file>"
}
```

Notes:
- This route is intended for public nurse self-registration and creates a user account automatically.
- It creates a pending nurse record and returns an auth token.

Success response:

```json
{
  "token": "abc123...",
  "access": "abc123...",
  "nurse": {
    "id": 42,
    "nanm_id": null,
    "full_name": "Grace Ibrahim",
    "email": "nurse@example.com",
    "phone": "08030000001",
    "photo": "/media/nurse_photos/....jpg",
    "licence_number": "PLT-LIC-00001",
    "licence_expiry": "2027-01-15",
    "licence_status": "Pending",
    "specialty": "General Nursing",
    "cadre": "Nurse",
    "employer": "Plateau Specialist Hospital",
    "ward": "Ward 1",
    "record_status": "pending",
    "employer_confirmed_at": null,
    "employment_confirmed": false,
    "created_at": "2026-11-03T10:00:00Z"
  }
}
```

#### `GET /api/v1/me/`
Return identity and role information for current user.

- Auth: required
- Response fields:
  - `id`
  - `email`
  - `role`
  - `nurse`
  - `employers`

Example:

```json
{
  "id": 12,
  "email": "hr@plateauhospital.test",
  "role": "hr",
  "nurse": null,
  "employers": [
    { "id": 3, "name": "Plateau Specialist Hospital" }
  ]
}
```

#### `GET /api/v1/nurse/profile/`
Return the nurse profile for the authenticated nurse account.

- Auth: required
- Use case: display profile and status dashboard

Example response:

```json
{
  "id": 42,
  "nanm_id": "PLT-NUR-000001",
  "full_name": "Grace Ibrahim",
  "email": "nurse@example.com",
  "phone": "08030000001",
  "photo": "/media/nurse_photos/....jpg",
  "licence_number": "PLT-LIC-00001",
  "licence_expiry": "2027-01-15",
  "licence_status": "Licensed",
  "specialty": "General Nursing",
  "cadre": "Nurse",
  "employer": "Plateau Specialist Hospital",
  "ward": "Ward 1",
  "record_status": "approved",
  "employer_confirmed_at": "2026-11-01T12:00:00Z",
  "employment_confirmed": true,
  "created_at": "2026-11-03T10:00:00Z"
}
```

#### `POST /api/v1/nurse/renew/`
Submit a renewal application for a nurse's licence.

- Auth: required
- Role: authenticated nurse account only
- Input:
  - `licence_expiry` as ISO date
  - `file` as uploaded licence document

Success response:

```json
{
  "id": 15,
  "decision": "pending",
  "document_type": "renewal"
}
```

Rules:
- Available only if the nurse record is approved
- Requires a future expiry date
- Requires a valid uploaded file

#### `GET /api/v1/nurse/activity/`
Return nurse document activity and notifications.

- Auth: required
- Response shape:

```json
{
  "documents": [
    {
      "id": 8,
      "document_type": "initial",
      "uploaded_at": "2026-11-03T10:15:00Z",
      "decision": "approved",
      "reason": "",
      "proposed_expiry": null
    }
  ],
  "notifications": [
    {
      "id": 2,
      "type": "expiry_reminder",
      "licence_expiry": "2027-01-15",
      "sent_at": "2026-11-03T10:00:00Z",
      "status": "sent"
    }
  ]
}
```

#### `GET /api/v1/nurse/card/`
Generate card metadata for an approved nurse.

- Auth: required
- Only available when the nurse is approved and has a NANNM ID

Example success:

```json
{
  "available": true,
  "signed_url": "http://localhost:8000/card/abc123.../",
  "qr_url": "http://localhost:8000/verify/PLT-NUR-000001/qr/",
  "nurse": {
    "id": 42,
    "nanm_id": "PLT-NUR-000001",
    "full_name": "Grace Ibrahim",
    "email": "nurse@example.com",
    "phone": "08030000001",
    "photo": "/media/nurse_photos/....jpg",
    "licence_number": "PLT-LIC-00001",
    "licence_expiry": "2027-01-15",
    "licence_status": "Licensed",
    "specialty": "General Nursing",
    "cadre": "Nurse",
    "employer": "Plateau Specialist Hospital",
    "ward": "Ward 1",
    "record_status": "approved",
    "employer_confirmed_at": "2026-11-01T12:00:00Z",
    "employment_confirmed": true,
    "created_at": "2026-11-03T10:00:00Z"
  }
}
```

---

### HR routes

#### `GET /api/v1/hr/nurses/`
Return nurses visible to HR staff or reviewer roles.

- Auth: required
- Access: `HR` users or staff reviewers
- Purpose: show employer-scoped nurse list for hospital administration

Example response:

```json
[
  {
    "id": 42,
    "nanm_id": "PLT-NUR-000001",
    "full_name": "Grace Ibrahim",
    "email": "nurse@example.com",
    "phone": "08030000001",
    "photo": "/media/nurse_photos/....jpg",
    "licence_number": "PLT-LIC-00001",
    "licence_expiry": "2027-01-15",
    "licence_status": "Licensed",
    "specialty": "General Nursing",
    "cadre": "Nurse",
    "employer": "Plateau Specialist Hospital",
    "ward": "Ward 1",
    "record_status": "approved",
    "employer_confirmed_at": "2026-11-01T12:00:00Z",
    "employment_confirmed": true,
    "created_at": "2026-11-03T10:00:00Z"
  }
]
```

#### `POST /api/v1/hr/nurses/<pk>/confirm/`
Confirm a nurse belongs to the HR user's employer.

- Auth: required
- Role: `HR` only
- Access: only nurses belonging to the HR user's employer

Success response:

```json
{
  "id": 42,
  "nanm_id": "PLT-NUR-000001",
  "full_name": "Grace Ibrahim",
  "employment_confirmed": true,
  "employer_confirmed_at": "2026-11-03T12:10:00Z"
}
```

#### `POST /api/v1/hr/register/`
Submit an HR registration request.

- Public access: yes
- Purpose: allow an HR user to register and wait for super-admin review
- Request body:

```json
{
  "email": "hr@plateauhospital.test",
  "hospital_name": "Plateau Specialist Hospital",
  "employer_type": "hospital",
  "lga": "Jos North",
  "contact_email": "contact@plateauhospital.test",
  "password": "StrongPass123!"
}
```

Success response:

```json
{
  "id": 10,
  "status": "pending"
}
```

#### `GET /api/v1/hr/employers/`
Return approved employer choices for UI selection.

Response shape:

```json
[
  {
    "id": 1,
    "name": "Plateau Specialist Hospital",
    "type": "hospital",
    "lga": "Jos North"
  }
]
```

---

### Super-admin and staff review routes

#### `GET /api/v1/admin/renewals/`
List pending renewal documents.

- Auth: required
- Role: Supervisor or Super Admin

Response:

```json
[
  {
    "id": 19,
    "nurse_id": 42,
    "name": "Grace Ibrahim",
    "nanm_id": "PLT-NUR-000001",
    "employer": "Plateau Specialist Hospital",
    "licence_number": "PLT-LIC-00001",
    "proposed_expiry": "2027-01-15",
    "uploaded_at": "2026-11-03T10:00:00Z"
  }
]
```

#### `POST /api/v1/admin/renewals/<pk>/`
Approve or reject renewal document.

Request body:

```json
{
  "action": "approve",
  "reason": "Optional review reason"
}
```

Valid actions:
- `approve`
- `reject`

Success response:

```json
{
  "id": 19,
  "decision": "approved",
  "reason": ""
}
```

#### `GET /api/v1/admin/summary/`
Return dashboard summary counts for the review/admin screens.

- Auth: required
- Role: Supervisor or Super Admin

Example response:

```json
{
  "total_nurses": 248,
  "pending_nurses": 14,
  "active_licences": 189,
  "expiring_licences": 21,
  "expired_licences": 12,
  "restricted_nurses": 7,
  "pending_hr_registrations": 3,
  "pending_renewals": 5,
  "recent_nurses": [
    {
      "id": 1,
      "full_name": "Amina Musa",
      "nanm_id": "PLT-NUR-000001",
      "employer__name": "Plateau Specialist Hospital",
      "record_status": "approved",
      "created_at": "2026-11-03T10:00:00Z"
    }
  ]
}
```

#### `GET /api/v1/admin/nurses/`
List or search nurse records.

Query params:
- `search` — free-text filter
- `status` — nurse record status
- `employer` — employer id

#### `GET /api/v1/admin/nurses/<pk>/`
Return a single nurse record with document metadata.

#### `POST /api/v1/admin/nurses/`
Create a nurse record from the admin side.

- Auth: required
- Role: Supervisor or Super Admin
- Requires super-admin for full record creation workflows

#### `PATCH /api/v1/admin/nurses/<pk>/`
Update a nurse record.

#### `DELETE /api/v1/admin/nurses/<pk>/`
Delete a nurse record.

#### `GET /api/v1/admin/hr-users/`
List HR user accounts.

#### `POST /api/v1/admin/hr-users/`
Create a direct HR user account.

#### `PATCH /api/v1/admin/hr-users/<pk>/`
Update HR user account details.

#### `DELETE /api/v1/admin/hr-users/<pk>/`
Delete HR user account.

#### `GET /api/v1/admin/supervisors/`
List supervisor accounts.

#### `POST /api/v1/admin/supervisors/`
Create a supervisor account.

#### `PATCH /api/v1/admin/supervisors/<pk>/`
Update a supervisor account.

#### `DELETE /api/v1/admin/supervisors/<pk>/`
Delete a supervisor account.

---

### HR registration review routes

#### `GET /api/v1/admin/hr-registrations/`
List HR applications still pending review.

#### `POST /api/v1/admin/hr-registrations/<pk>/`
Review an HR registration request.

Request body:

```json
{
  "action": "approve",
  "reason": "Optional rejection reason"
}
```

Valid actions:
- `approve`
- `reject`

On approve:
- Employer is created or fetched
- HR user is created/attached to the employer
- Request status is set to `approved`

On reject:
- Request status is set to `rejected`
- Optional reason is stored

---

## Permissions Model

Current backend behavior is based on the registry permission checks.

### Active reviewer roles
- `Supervisor`
- `Super Admin`
- `HR`

### Notes on role behavior
- `Supervisor` and `Super Admin` are authorized for review and transitions.
- `HR` is employer-scoped and should only see nurses for their designated employer.
- Public routes do not require auth.
- Protected endpoints require valid auth tokens.

---

## Error Handling Pattern

The API follows DRF patterns.

Common error responses:

```json
{
  "detail": "Permission denied."
}
```

or

```json
{
  "field_name": ["Validation message"]
}
```

Examples:
- invalid login: `400 Bad Request`
- invalid payload: `400 Bad Request`
- forbidden access: `403 Forbidden`
- missing resource: `404 Not Found`

---

## Important Implementation Notes for Frontend Developers

1. `token_login` accepts `email`, not username.
2. `Authorization` is token-based, not session-based in the API contract.
3. Public verification uses `GET /api/v1/verify/<nanm_id>/`.
4. HR user registration is a distinct flow from nurse registration.
5. Some admin and HR APIs are broader than the current frontend screens and should be used carefully.
6. File uploads (`licence_scan`, `selfie`, `file`) are multipart form uploads, not JSON payloads.
7. The backend expects date strings in ISO format on some endpoints (for example `YYYY-MM-DD`).
8. `role` values returned by `/api/v1/me/` may be:
   - `hr`
   - `super_admin`
   - `supervisor`
   - `reviewer`
   - `nurse`
   - `user`

---

## Known Caveats

- Some admin endpoints are broader than what the frontend currently implements and may need route-specific guard logic.
- `review_renewal` and `admin_nurses` are powerful endpoints and should be treated as staff-only routes.
- For content upload endpoints, clients should send `FormData`, not JSON, whenever files are involved.
- Validation errors are not always serialized in a uniform shape across every endpoint; frontend code should tolerate field-level dictionaries and generic `detail` strings.

---

## Suggested Frontend Usage Order

1. `POST /api/v1/auth/token/`
2. `GET /api/v1/me/`
3. `GET /api/v1/nurse/profile/` for nurse dashboard
4. `GET /api/v1/hr/nurses/` for HR dashboard
5. `GET /api/v1/admin/summary/` for supervisor/admin dashboard
6. `POST /api/v1/nurse/renew/` for renewal flow
7. `GET /api/v1/verify/<nanm_id>/` for public verification
8. `POST /api/v1/hr/register/` for HR registration
9. `POST /api/v1/admin/hr-registrations/<pk>/` for staff review

---

## Recommended Next Step

Use this file as the source of truth for frontend implementation and keep it updated whenever endpoints change. For any new integration, confirm the exact route name, auth requirements, and payload shape before writing the frontend call.
