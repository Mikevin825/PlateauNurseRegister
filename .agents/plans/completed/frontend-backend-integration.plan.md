# Plan: Frontend Integration with Backend

## Summary

This plan connects the existing React frontend to the Django backend and closes the gap between the current mock/demo interface and the real registry workflow. The work prioritizes the backend contract, route alignment, auth/role guards, and the highest-value user journeys: public verification, nurse self-registration, nurse dashboard/profile, HR registration and review, and renewal/card flows.

## User Story

As a nurse, hospital HR user, or public verifier
I want the frontend to match the backend workflows and business rules
So that I can verify credentials, register, review records, and manage licensing through the live system instead of static demo screens.

## Metadata

| Field | Value |
|-------|-------|
| Type | ENHANCEMENT |
| Complexity | MEDIUM |
| Systems Affected | Django backend, DRF API, React frontend, route guards, auth/session flow |
| Jira Issue | N/A |

---

## Patterns to Follow

### Backend API pattern
```python
// SOURCE: /home/albasheer/Desktop/Silicon Plateau/api/views.py:1-19
@api_view(["GET"])
@permission_classes([AllowAny])
def verify_nurse(request, nanm_id):
    try:
        nurse = Nurse.objects.select_related("employer").get(nanm_id=nanm_id)
    except Nurse.DoesNotExist as exc:
        raise NotFound({"detail": "Not registered"}) from exc
    serializer = PublicNurseSerializer(nurse, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)
```

### Serializer output contract
```python
// SOURCE: /home/albasheer/Desktop/Silicon Plateau/api/serializers.py:1-30
class PublicNurseSerializer(serializers.ModelSerializer):
    licence_status = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    employer = serializers.SerializerMethodField()
```

### Django URL naming convention
```python
// SOURCE: /home/albasheer/Desktop/Silicon Plateau/registry/urls.py:1-28
urlpatterns = [
    path("register/", views.register, name="register"),
    path("verify/", views.verify, name="verify"),
    path("hr/register/", views.hr_registration, name="hr_registration"),
    path("nurses/<int:pk>/approval/", views.approval_confirmation, name="approval_confirmation"),
]
```

### Test-driven validation pattern
```python
// SOURCE: /home/albasheer/Desktop/Silicon Plateau/registry/tests.py:360-420
response = self.client.get(reverse("registry:register"))
self.assertEqual(response.status_code, 200)
self.assertContains(response, "Register")
```

### Frontend route pattern already present
```jsx
// SOURCE: /home/albasheer/Desktop/plateau-nurse-registry/src/App.jsx:1-160
<Routes>
  <Route path="/" element={<WelcomePage />} />
  <Route path="/nurse/login" element={<NurseLogin />} />
  <Route path="/nurse" element={<NurseLayout />}>
    <Route path="dashboard" element={<NurseDashboard />} />
    <Route path="profile" element={<NurseProfile />} />
    <Route path="licence" element={<LicenceManagement />} />
  </Route>
</Routes>
```

---

## Files to Change

| File | Action | Purpose |
|-------|--------|---------|
| `/home/albasheer/Desktop/plateau-nurse-registry/src/App.jsx` | UPDATE | Align app routes to backend workflow and add missing routes |
| `/home/albasheer/Desktop/plateau-nurse-registry/src/apiService.jsx` | UPDATE | Replace mock/incorrect API calls with real backend endpoints |
| `/home/albasheer/Desktop/plateau-nurse-registry/src/pages/PublicVerify.jsx` | UPDATE | Connect verify page to live public API |
| `/home/albasheer/Desktop/plateau-nurse-registry/src/pages/NurseRegister.jsx` | UPDATE | Implement live nurse self-registration form and upload flow |
| `/home/albasheer/Desktop/plateau-nurse-registry/src/pages/NurseDashboard.jsx` | UPDATE | Replace placeholder data with live profile/status fetches |
| `/home/albasheer/Desktop/plateau-nurse-registry/src/pages/LicenceManagement.jsx` | CREATE / UPDATE | Implement renewal upload and status tracking |
| `/home/albasheer/Desktop/plateau-nurse-registry/src/pages/DigitalIDCard.jsx` | UPDATE | Render printable signed card view |
| `/home/albasheer/Desktop/plateau-nurse-registry/src/pages/hr/HRDashboard.jsx` | UPDATE | Replace static metrics with employer-scoped data |
| `/home/albasheer/Desktop/plateau-nurse-registry/src/pages/hr/HRNurseDirectory.jsx` | UPDATE | List and filter employer nurses |
| `/home/albasheer/Desktop/plateau-nurse-registry/src/pages/hr/HREmploymentVerification.jsx` | UPDATE | Add employer confirmation flow |
| `/home/albasheer/Desktop/plateau-nurse-registry/src/pages/hr/HRLicenceMonitoring.jsx` | UPDATE | Show licensing health and expiry warning sections |
| `/home/albasheer/Desktop/plateau-nurse-registry/src/components/...` | CREATE / UPDATE | Add shared auth guard and layout improvements |
| `/home/albasheer/Desktop/Silicon Plateau/api/views.py` | REVIEW / UPDATE | Confirm API surface matches frontend needs |
| `/home/albasheer/Desktop/Silicon Plateau/registry/urls.py` | REVIEW | Confirm exposed routes align with UI requirements |

---

## Tasks

### Task 1: Establish API contract and environment config

- **File**: `/home/albasheer/Desktop/plateau-nurse-registry/src/apiService.jsx`
- **Action**: UPDATE
- **Implement**: Define a single backend base URL, consistent error handling, and clear functions for public verify, registration, profile fetch, and HR actions.
- **Mirror**: `api/views.py` and `api/serializers.py` as the canonical source of endpoint behavior.
- **Validate**: Run the frontend build and confirm no broken imports or undefined API methods.

### Task 2: Add auth and role-aware route guards

- **File**: `/home/albasheer/Desktop/plateau-nurse-registry/src/App.jsx`
- **Action**: UPDATE
- **Implement**: Add route wrappers for:
  - public pages
  - nurse pages
  - HR pages
  - super-admin-only review screens
- **Mirror**: backend permission model from `registry/permissions.py` and route patterns in `registry/urls.py`.
- **Validate**: Confirm that unauthorized users redirect to login or home.

### Task 3: Connect public verification flow

- **File**: `/home/albasheer/Desktop/plateau-nurse-registry/src/pages/PublicVerify.jsx`
- **Action**: UPDATE
- **Implement**: Replace the current demo verification message with the live public backend call to `GET /api/v1/verify/<nanm_id>/` and proper error states for not found or invalid IDs.
- **Mirror**: `api/views.py` result contract and `PublicNurseSerializer` fields.
- **Validate**: Verify a known valid NANNM ID and confirm the display matches `nanm_id`, `full_name`, `employer`, and `licence_status`.

### Task 4: Implement nurse registration and upload flow

- **File**: `/home/albasheer/Desktop/plateau-nurse-registry/src/pages/NurseRegister.jsx`
- **Action**: UPDATE
- **Implement**: Build a live registration submission flow using the existing Django form semantics: NIN, licence details, employer, selfie, licence scan, and consent.
- **Mirror**: `registry/forms.py` and `registry/views.py` for required payload fields and upload behavior.
- **Validate**: Submit a valid registration and confirm the record is created as `pending` with the expected redirect/success state.

### Task 5: Build live nurse dashboard and profile screens

- **Files**: `/home/albasheer/Desktop/plateau-nurse-registry/src/pages/NurseDashboard.jsx`, `/home/albasheer/Desktop/plateau-nurse-registry/src/pages/NurseProfile.jsx`
- **Action**: UPDATE
- **Implement**: Replace static placeholders with live data from guarded nurse endpoints and display status, employer, expiry, and NANNM ID.
- **Mirror**: `registry/models.py` `Nurse` fields and `registry/views.py` protected data logic.
- **Validate**: Render fallback states for pending, approved, suspended, and expired records.

### Task 6: Implement renewal and licence management

- **Files**: `/home/albasheer/Desktop/plateau-nurse-registry/src/pages/LicenceManagement.jsx`, `/home/albasheer/Desktop/plateau-nurse-registry/src/pages/NurseNotifications.jsx`
- **Action**: CREATE / UPDATE
- **Implement**: Add renewal submission, expiry reminders, and document review status UI. Include document type selection and reason display if rejected.
- **Mirror**: `registry/models.py` `LicenceDocument` and route entry in `registry/urls.py` for renewal actions.
- **Validate**: Confirm a renewal request uploads and shows pending status until staff review.

### Task 7: Implement digital ID card and signed link view

- **File**: `/home/albasheer/Desktop/plateau-nurse-registry/src/pages/DigitalIDCard.jsx`
- **Action**: UPDATE
- **Implement**: Show the approved nurse card, QR code, direct link, and signed-link display consistent with backend card views.
- **Mirror**: backend `card()`, `signed_card()`, and `nurse_qr()` behavior in `registry/views.py`.
- **Validate**: Confirm the card renders successfully and signed-token invalid states display the error page.

### Task 8: Build HR portal and employer-scoped views

- **Files**: `/home/albasheer/Desktop/plateau-nurse-registry/src/pages/hr/HRDashboard.jsx`, `/home/albasheer/Desktop/plateau-nurse-registry/src/pages/hr/HRNurseDirectory.jsx`, `/home/albasheer/Desktop/plateau-nurse-registry/src/pages/hr/HREmploymentVerification.jsx`, `/home/albasheer/Desktop/plateau-nurse-registry/src/pages/hr/HRLicenceMonitoring.jsx`
- **Action**: UPDATE
- **Implement**: Replace demo values with employer-scoped nurse lists and verification actions.
- **Mirror**: `filter_employers_for_user()` and `nurses_for_user()` from `registry/permissions.py`.
- **Validate**: Confirm HR accounts only see nurses tied to their employer and cannot access unrelated records.

### Task 9: Add HR self-registration and super-admin review screens

- **Files**: `/home/albasheer/Desktop/plateau-nurse-registry/src/pages/HospitalLogin.jsx`, `/home/albasheer/Desktop/plateau-nurse-registry/src/pages/hr/HRSectionPlaceholder.jsx`, plus new route screens for review
- **Action**: CREATE / UPDATE
- **Implement**: Build the HR self-registration form and the super-admin review page to approve or reject hospital registrations.
- **Mirror**: `HRRegistrationForm` in `registry/forms.py` and `approve_hr_registration()` in `registry/views.py`.
- **Validate**: Submit an HR request and confirm the super-admin status flow works end-to-end.

### Task 10: Finish QA and release readiness

- **Files**: frontend pages and shared UI components
- **Action**: FINALIZE
- **Implement**: Standardize loading, error, empty, and no-access states; clean route naming; ensure responsive behaviour; remove stale mock data.
- **Mirror**: backend test patterns and admin flows in `registry/tests.py`.
- **Validate**: Run the frontend build and smoke-test the user journeys.

---

## Validation

```bash
# Frontend build
cd /home/albasheer/Desktop/plateau-nurse-registry && npm run build

# Lint
cd /home/albasheer/Desktop/plateau-nurse-registry && npm run lint

# Backend verification
cd /home/albasheer/Desktop/Silicon\ Plateau && python manage.py test
```

---

## Acceptance Criteria

- [ ] All critical frontend routes match the backend URL surface and role model
- [ ] Public verification works against the live backend API
- [ ] Nurse self-registration works with file uploads and consent flow
- [ ] Nurse dashboard/profile are powered by real record data
- [ ] HR portal is employer-scoped and read-only where appropriate
- [ ] HR self-registration and super-admin review flow are implemented
- [ ] Renewal and card workflows are connected to backend endpoints
- [ ] Build passes and the app is ready for a smoke-test pass
