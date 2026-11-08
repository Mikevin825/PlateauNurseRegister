"""Seed fictional, repeatable demonstration data for the Plateau Nurse Registry.

Everything this command creates is fictitious. Demo employers carry a ``(Demo)``
suffix and demo licence numbers carry a ``PLT-LIC-DEMO-`` prefix, so no record
produced here can be mistaken for a real nurse, a real employer, or a genuine
regulator-issued licence.

The command is idempotent: running it again refreshes the demo records in place
and creates no duplicates. Records that are not part of the demo dataset are
never created, modified or deleted.

    python manage.py seed_demo            # create or refresh the demo dataset
    python manage.py seed_demo --reset    # delete demo data first, then reseed

Nurses are created through the real ``NurseRegistrationForm`` (as a reviewing
officer), moved between statuses through ``registry.services.transition_nurse``
(the same call the admin actions and the review API use), and have their
employment confirmed or rejected through the real HR API endpoints. Status is
never assigned directly.
"""

import re
from collections import deque
from datetime import timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Q
from django.test import override_settings
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from registry.forms import NurseRegistrationForm
from registry.models import Employer, LicenceDocument, Nurse
from registry.permissions import HR, OFFICER, SUPER_ADMIN, SUPERVISOR
from registry.services import ALLOWED_TRANSITIONS, transition_nurse

DEMO_PASSWORD = "DemoPass123!"
DEMO_DOMAIN = "example.test"
DEMO_LICENCE_PREFIX = "PLT-LIC-DEMO-"

# Every employer name ends in " (Demo)" so the organisation is identifiable as
# test data wherever the registry displays it.
DEMO_EMPLOYERS = {
    "Plateau Specialist Hospital (Demo)": ("hospital", "Jos North"),
    "Jos North General Hospital (Demo)": ("hospital", "Jos North"),
    "Jos South Comprehensive Health Centre (Demo)": ("primary_health_centre", "Jos South"),
    "Vom Christian Clinic (Demo)": ("clinic", "Jos South"),
    "Pankshin Mission Hospital (Demo)": ("hospital", "Pankshin"),
}

# username: (email, [groups], is_staff, is_superuser)
DEMO_USERS = {
    "demo_superadmin": ("superadmin@example.test", [SUPER_ADMIN], True, True),
    "demo_officer1": ("officer1@example.test", [OFFICER], True, False),
    "demo_supervisor": ("supervisor@example.test", [SUPERVISOR], True, False),
    "demo_hr1": ("hr1@example.test", [HR], False, False),
    "demo_hr2": ("hr2@example.test", [HR], False, False),
    "demo_hr3": ("hr3@example.test", [HR], False, False),
    "demo_hr4": ("hr4@example.test", [HR], False, False),
    "demo_hr5": ("hr5@example.test", [HR], False, False),
}

# Logins attached to approved nurses so the digital ID card can be demonstrated.
DEMO_NURSE_ACCOUNTS = ("demo_nurse1", "demo_nurse2", "demo_nurse3", "demo_nurse4")

DEMO_HR_BY_EMPLOYER = {
    "Plateau Specialist Hospital (Demo)": "demo_hr1",
    "Jos North General Hospital (Demo)": "demo_hr2",
    "Jos South Comprehensive Health Centre (Demo)": "demo_hr3",
    "Vom Christian Clinic (Demo)": "demo_hr4",
    "Pankshin Mission Hospital (Demo)": "demo_hr5",
}

# licence_expiry is a day offset from today so the demo always shows live
# green / yellow / red licence states whenever it is run.
# target_status is reached through the real transition workflow.
# employment is decided through the real HR API (confirmed / rejected / pending).
DEMO_NURSES = (
    {
        "scenario": "Approved, licence valid, employment confirmed",
        "full_name": "Amina Adamu",
        "phone": "08030000001",
        "email": "amina.adamu@example.test",
        "nin": "90000000001",
        "licence_number": "PLT-LIC-DEMO-0001",
        "licence_expiry_days": 400,
        "specialty": "General Nursing",
        "cadre": "Nurse",
        "employer": "Plateau Specialist Hospital (Demo)",
        "ward": "Medical Ward",
        "target_status": "approved",
        "employment": "confirmed",
        "nurse_account": "demo_nurse1",
    },
    {
        "scenario": "Approved, licence valid, employment confirmed",
        "full_name": "Grace Danjuma",
        "phone": "08030000002",
        "email": "grace.danjuma@example.test",
        "nin": "90000000002",
        "licence_number": "PLT-LIC-DEMO-0002",
        "licence_expiry_days": 380,
        "specialty": "Midwifery",
        "cadre": "Midwife",
        "employer": "Plateau Specialist Hospital (Demo)",
        "ward": "Labour Ward",
        "target_status": "approved",
        "employment": "confirmed",
        "nurse_account": "demo_nurse2",
    },
    {
        "scenario": "Approved, licence valid, employment awaiting verification",
        "full_name": "Blessing Ibrahim",
        "phone": "08030000003",
        "email": "blessing.ibrahim@example.test",
        "nin": "90000000003",
        "licence_number": "PLT-LIC-DEMO-0003",
        "licence_expiry_days": 350,
        "specialty": "Community Health",
        "cadre": "Community Health Nurse",
        "employer": "Jos North General Hospital (Demo)",
        "ward": "Community Clinic",
        "target_status": "approved",
        "employment": "pending",
    },
    {
        "scenario": "Approved, licence valid, employment awaiting verification",
        "full_name": "Esther Musa",
        "phone": "08030000004",
        "email": "esther.musa@example.test",
        "nin": "90000000004",
        "licence_number": "PLT-LIC-DEMO-0004",
        "licence_expiry_days": 340,
        "specialty": "Paediatric Nursing",
        "cadre": "Nurse",
        "employer": "Jos South Comprehensive Health Centre (Demo)",
        "ward": "Children's Ward",
        "target_status": "approved",
        "employment": "pending",
        "nurse_account": "demo_nurse3",
    },
    {
        "scenario": "Approved, licence expiring soon",
        "full_name": "Mary Pam",
        "phone": "08030000005",
        "email": "mary.pam@example.test",
        "nin": "90000000005",
        "licence_number": "PLT-LIC-DEMO-0005",
        "licence_expiry_days": 90,
        "specialty": "Mental Health",
        "cadre": "Nurse/Midwife",
        "employer": "Plateau Specialist Hospital (Demo)",
        "ward": "Psychiatric Unit",
        "target_status": "approved",
        "employment": "confirmed",
    },
    {
        "scenario": "Approved, licence expiring inside the reminder window",
        "full_name": "Joy Terna",
        "phone": "08030000006",
        "email": "joy.terna@example.test",
        "nin": "90000000006",
        "licence_number": "PLT-LIC-DEMO-0006",
        "licence_expiry_days": 20,
        "specialty": "General Nursing",
        "cadre": "Nurse",
        "employer": "Vom Christian Clinic (Demo)",
        "ward": "Outpatient Department",
        "target_status": "approved",
        "employment": "pending",
        "renewal_proposed_expiry_days": 365,
    },
    {
        "scenario": "Approved, licence expired",
        "full_name": "Hauwa Yakubu",
        "phone": "08030000007",
        "email": "hauwa.yakubu@example.test",
        "nin": "90000000007",
        "licence_number": "PLT-LIC-DEMO-0007",
        "licence_expiry_days": -30,
        "specialty": "Midwifery",
        "cadre": "Midwife",
        "employer": "Jos North General Hospital (Demo)",
        "ward": "Antenatal Clinic",
        "target_status": "approved",
        "employment": "confirmed",
    },
    {
        "scenario": "Approved, licence expired",
        "full_name": "Ruth Bala",
        "phone": "08030000008",
        "email": "ruth.bala@example.test",
        "nin": "90000000008",
        "licence_number": "PLT-LIC-DEMO-0008",
        "licence_expiry_days": -120,
        "specialty": "General Nursing",
        "cadre": "Nurse",
        "employer": "Pankshin Mission Hospital (Demo)",
        "ward": "Surgical Ward",
        "target_status": "approved",
        "employment": "pending",
    },
    {
        "scenario": "Pending registration awaiting review",
        "full_name": "Deborah James",
        "phone": "08030000009",
        "email": "deborah.james@example.test",
        "nin": "90000000009",
        "licence_number": "PLT-LIC-DEMO-0009",
        "licence_expiry_days": 365,
        "specialty": "General Nursing",
        "cadre": "Nurse",
        "employer": "Plateau Specialist Hospital (Demo)",
        "ward": "Medical Ward",
        "target_status": "pending",
        "employment": "pending",
    },
    {
        "scenario": "Pending registration awaiting review",
        "full_name": "Lydia Sani",
        "phone": "08030000010",
        "email": "lydia.sani@example.test",
        "nin": "90000000010",
        "licence_number": "PLT-LIC-DEMO-0010",
        "licence_expiry_days": 200,
        "specialty": "Community Health",
        "cadre": "Community Health Nurse",
        "employer": "Jos North General Hospital (Demo)",
        "ward": "Community Clinic",
        "target_status": "pending",
        "employment": "pending",
    },
    {
        "scenario": "Rejected registration",
        "full_name": "Naomi Uche",
        "phone": "08030000011",
        "email": "naomi.uche@example.test",
        "nin": "90000000011",
        "licence_number": "PLT-LIC-DEMO-0011",
        "licence_expiry_days": 300,
        "specialty": "General Nursing",
        "cadre": "Nurse",
        "employer": "Jos South Comprehensive Health Centre (Demo)",
        "ward": "Outpatient Department",
        "target_status": "rejected",
        "employment": "pending",
    },
    {
        "scenario": "Rejected registration",
        "full_name": "Rebecca Okafor",
        "phone": "08030000012",
        "email": "rebecca.okafor@example.test",
        "nin": "90000000012",
        "licence_number": "PLT-LIC-DEMO-0012",
        "licence_expiry_days": 250,
        "specialty": "Paediatric Nursing",
        "cadre": "Nurse",
        "employer": "Vom Christian Clinic (Demo)",
        "ward": "Children's Ward",
        "target_status": "rejected",
        "employment": "pending",
    },
    {
        "scenario": "Suspended registration",
        "full_name": "Sarah Nwosu",
        "phone": "08030000013",
        "email": "sarah.nwosu@example.test",
        "nin": "90000000013",
        "licence_number": "PLT-LIC-DEMO-0013",
        "licence_expiry_days": 200,
        "specialty": "Mental Health",
        "cadre": "Nurse",
        "employer": "Plateau Specialist Hospital (Demo)",
        "ward": "Psychiatric Unit",
        "target_status": "suspended",
        "employment": "confirmed",
    },
    {
        "scenario": "Revoked registration",
        "full_name": "Martha Garba",
        "phone": "08030000014",
        "email": "martha.garba@example.test",
        "nin": "90000000014",
        "licence_number": "PLT-LIC-DEMO-0014",
        "licence_expiry_days": 200,
        "specialty": "Midwifery",
        "cadre": "Midwife",
        "employer": "Jos North General Hospital (Demo)",
        "ward": "Labour Ward",
        "target_status": "revoked",
        "employment": "confirmed",
    },
    {
        "scenario": "Flagged registration under investigation",
        "full_name": "Priscilla Rwang",
        "phone": "08030000015",
        "email": "priscilla.rwang@example.test",
        "nin": "90000000015",
        "licence_number": "PLT-LIC-DEMO-0015",
        "licence_expiry_days": 300,
        "specialty": "General Nursing",
        "cadre": "Nurse",
        "employer": "Jos South Comprehensive Health Centre (Demo)",
        "ward": "Medical Ward",
        "target_status": "flagged",
        "employment": "pending",
    },
    {
        "scenario": "Approved, employment claim rejected by HR",
        "full_name": "Comfort Kalu",
        "phone": "08030000016",
        "email": "comfort.kalu@example.test",
        "nin": "90000000016",
        "licence_number": "PLT-LIC-DEMO-0016",
        "licence_expiry_days": 320,
        "specialty": "Community Health",
        "cadre": "Community Health Nurse",
        "employer": "Vom Christian Clinic (Demo)",
        "ward": "Community Clinic",
        "target_status": "approved",
        "employment": "rejected",
    },
    {
        "scenario": "Approved, licence valid, employment confirmed",
        "full_name": "Faith Wuyep",
        "phone": "08030000017",
        "email": "faith.wuyep@example.test",
        "nin": "90000000017",
        "licence_number": "PLT-LIC-DEMO-0017",
        "licence_expiry_days": 390,
        "specialty": "General Nursing",
        "cadre": "Nurse",
        "employer": "Pankshin Mission Hospital (Demo)",
        "ward": "Medical Ward",
        "target_status": "approved",
        "employment": "confirmed",
        "nurse_account": "demo_nurse4",
    },
    {
        "scenario": "Pending registration awaiting review",
        "full_name": "Hope Zamani",
        "phone": "08030000018",
        "email": "hope.zamani@example.test",
        "nin": "90000000018",
        "licence_number": "PLT-LIC-DEMO-0018",
        "licence_expiry_days": 280,
        "specialty": "General Nursing",
        "cadre": "Nurse",
        "employer": "Plateau Specialist Hospital (Demo)",
        "ward": "Surgical Ward",
        "target_status": "pending",
        "employment": "pending",
    },
)

# Reasons recorded on the audit trail for transitions that require one.
TRANSITION_REASONS = {
    "rejected": "Demo dataset: registration does not meet the sample requirements.",
    "flagged": "Demo dataset: document needs a second review.",
    "suspended": "Demo dataset: licence misuse under investigation.",
    "revoked": "Demo dataset: serious breach confirmed.",
}

# A pending renewal application for the nurse whose licence is closest to expiry.
DEMO_RENEWAL_LICENCE = "PLT-LIC-DEMO-0006"

# --- Legacy demo data produced by the previous version of this command ---------
# Kept so `--reset` can clear the superseded 60-record dataset.
LEGACY_DEMO_EMPLOYERS = {
    "Plateau Specialist Hospital",
    "Bingham University Teaching Hospital",
    "Jos South Comprehensive Health Centre",
    "Vom Christian Clinic",
}
LEGACY_DEMO_USERNAMES = {
    "demo_superadmin",
    "demo_officer1",
    "demo_officer2",
    "demo_supervisor",
    "demo_hr1",
    "demo_hr2",
    "demo_nurse",
}
LEGACY_LICENCE_PATTERN = re.compile(r"^PLT-LIC-\d{5}$")

MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
    b"trailer\n<< /Root 1 0 R >>\n%%EOF\n"
)


def _placeholder_selfie(initials, colour):
    """Return a generated JPEG placeholder portrait (never a real photograph)."""
    buffer = BytesIO()
    image = Image.new("RGB", (480, 480), colour)
    try:
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default(size=180)
        box = draw.textbbox((0, 0), initials, font=font)
        width, height = box[2] - box[0], box[3] - box[1]
        draw.text(
            ((480 - width) / 2 - box[0], (480 - height) / 2 - box[1]),
            initials,
            fill=(255, 255, 255),
            font=font,
        )
    except Exception:
        # A flat colour placeholder is still a valid image asset.
        pass
    image.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


# ``approved`` is the normal gateway to every post-approval status, so it is
# explored first. Without this the BFS may return e.g. pending -> flagged ->
# revoked, which never issues a NANNM ID and raises a Flag for a revoked record.
TRANSITION_PREFERENCE = {"approved": 0}


def _transition_path(start, target):
    """Shortest allowed transition path from ``start`` to ``target`` (BFS).

    Neighbours are visited in a deterministic order that prefers approval, so
    the same inputs always produce the same path.
    """
    if start == target:
        return []
    queue = deque([(start, [])])
    seen = {start}
    while queue:
        status, path = queue.popleft()
        neighbours = sorted(
            ALLOWED_TRANSITIONS.get(status, ()),
            key=lambda name: (TRANSITION_PREFERENCE.get(name, 1), name),
        )
        for nxt in neighbours:
            if nxt in seen:
                continue
            new_path = path + [nxt]
            if nxt == target:
                return new_path
            seen.add(nxt)
            queue.append((nxt, new_path))
    return None


class Command(BaseCommand):
    help = (
        "Create or refresh the fictional demonstration dataset. "
        "Idempotent: safe to run repeatedly; use --reset to clear demo data first."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help=(
                "Delete existing demonstration data (including the legacy "
                "60-record dataset) before seeding."
            ),
        )

    def handle(self, *args, **options):
        # Divert outbound email for the whole run. This command only creates
        # local demonstration data, so it must not depend on, or attempt, real
        # SMTP delivery for rejection notices and expiry reminders.
        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
        ):
            if options["reset"]:
                self._reset()

            call_command("setup_groups", stdout=self.stdout)

            employers = self._ensure_employers()
            users = self._ensure_users()
            self._ensure_hr_links(employers, users)
            self._ensure_nurses(employers, users)

            # Expiry reminders come from the real command so the nurse
            # dashboard shows a genuine notification.
            call_command("send_expiry_reminders", stdout=self.stdout)

        self._print_summary()

    # --- employers and users -------------------------------------------------

    def _ensure_employers(self):
        employers = {}
        for name, (employer_type, lga) in DEMO_EMPLOYERS.items():
            employer, created = Employer.objects.get_or_create(
                name=name,
                defaults={
                    "type": employer_type,
                    "lga": lga,
                    "contact_email": f"{name.split()[0].lower()}@{DEMO_DOMAIN}",
                    "approved": True,
                },
            )
            employer.type = employer_type
            employer.lga = lga
            employer.approved = True
            employer.save()
            employers[name] = employer
            self.stdout.write(
                f"  employer {'created' if created else 'updated'}: {name}"
            )
        return employers

    def _ensure_users(self):
        User = get_user_model()
        users = {}
        for username, (email, group_names, is_staff, is_superuser) in DEMO_USERS.items():
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "is_staff": is_staff,
                    "is_superuser": is_superuser,
                },
            )
            user.email = email
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.set_password(DEMO_PASSWORD)
            user.save()
            user.groups.set(Group.objects.filter(name__in=group_names))
            users[username] = user
            self.stdout.write(
                f"  account {'created' if created else 'updated'}: {username} "
                f"({', '.join(group_names) or 'no group'})"
            )
        return users

    def _ensure_hr_links(self, employers, users):
        for employer_name, username in DEMO_HR_BY_EMPLOYER.items():
            employers[employer_name].hr_users.add(users[username])

    # --- nurses --------------------------------------------------------------

    def _ensure_nurses(self, employers, users):
        officer = users["demo_officer1"]
        supervisor = users["demo_supervisor"]

        for spec in DEMO_NURSES:
            employer = employers[spec["employer"]]
            expiry = timezone.localdate() + timedelta(days=spec["licence_expiry_days"])
            nurse = Nurse.objects.filter(
                licence_number=spec["licence_number"]
            ).first()

            if nurse is None:
                nurse = self._register_nurse(spec, employer, expiry, officer)
                action = "created"
            else:
                self._refresh_nurse(nurse, spec, employer, expiry)
                action = "updated"

            status_note = self._apply_status(nurse, spec["target_status"], supervisor)
            employment_note = self._apply_employment(nurse, spec, users)
            self._ensure_initial_document(nurse, spec, supervisor)
            self._ensure_renewal_document(nurse, spec)

            if spec.get("nurse_account"):
                self._ensure_nurse_account(nurse, spec)

            self.stdout.write(
                f"  nurse {action}: {spec['full_name']} [{spec['licence_number']}]"
                f" | {spec['scenario']}"
                f" | {status_note}"
                f" | {employment_note}"
            )

        demo_count = Nurse.objects.filter(
            licence_number__startswith=DEMO_LICENCE_PREFIX
        ).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo nurses: {demo_count} | all nurses: {Nurse.objects.count()}"
            )
        )

    def _register_nurse(self, spec, employer, expiry, officer):
        """Create a pending nurse through the real registration form."""
        initials = "".join(part[0] for part in spec["full_name"].split()[:2]).upper()
        colour = (37, 99, 235) if len(spec["full_name"]) % 2 else (16, 122, 87)
        suffix = spec["licence_number"][-4:]
        selfie = SimpleUploadedFile(
            f"demo_selfie_{suffix}.jpg",
            _placeholder_selfie(initials, colour),
            content_type="image/jpeg",
        )
        scan = SimpleUploadedFile(
            f"demo_licence_{suffix}.pdf",
            MINIMAL_PDF,
            content_type="application/pdf",
        )

        form = NurseRegistrationForm(
            {
                "full_name": spec["full_name"],
                "phone": spec["phone"],
                "email": spec["email"],
                "licence_number": spec["licence_number"],
                "licence_expiry": expiry.isoformat(),
                "specialty": spec["specialty"],
                "cadre": spec["cadre"],
                "employer": employer.pk,
                "ward": spec["ward"],
                "nin": spec["nin"],
                "consent": "on",
            },
            {"selfie": selfie, "licence_scan": scan},
            user=officer,
        )
        if not form.is_valid():
            raise CommandError(
                f"Could not register demo nurse {spec['full_name']}: "
                f"{form.errors.as_json()}"
            )

        nurse = form.save()
        LicenceDocument.objects.create(
            nurse=nurse,
            file=scan,
            document_type=LicenceDocument.DocumentType.INITIAL,
        )
        return nurse

    def _refresh_nurse(self, nurse, spec, employer, expiry):
        """Bring an existing demo nurse back in line with the demo specification."""
        nurse.full_name = spec["full_name"]
        nurse.phone = spec["phone"]
        nurse.email = spec["email"]
        nurse.licence_number = spec["licence_number"]
        nurse.licence_expiry = expiry
        nurse.specialty = spec["specialty"]
        nurse.cadre = spec["cadre"]
        nurse.employer = employer
        nurse.ward = spec["ward"]
        nurse.save()

    def _apply_status(self, nurse, target, supervisor):
        """Move the nurse to the target status through the real workflow."""
        nurse.refresh_from_db()
        if nurse.record_status == target:
            return f"status {target} (unchanged)"

        path = _transition_path(nurse.record_status, target)
        if path is None:
            return (
                f"status left as {nurse.record_status}; no allowed transition to {target}"
            )

        start = nurse.record_status
        previous = start
        for step in path:
            reason = TRANSITION_REASONS.get(step, "")
            # Every transition except pending -> approved requires a reason.
            if not reason and not (previous == "pending" and step == "approved"):
                reason = "Demo dataset refresh."
            transition_nurse(supervisor, nurse, step, reason)
            previous = step
            nurse.refresh_from_db()
        return "status " + " -> ".join([start, *path])

    def _apply_employment(self, nurse, spec, users):
        """Confirm or reject employment through the real HR API endpoints."""
        decision = spec["employment"]
        if decision == "pending":
            return "employment pending"

        nurse.refresh_from_db()
        if nurse.employment_status == decision:
            return f"employment {decision} (unchanged)"

        if nurse.employment_status != Nurse.EmploymentStatus.PENDING:
            return (
                f"employment left as {nurse.employment_status}; "
                "a decided record cannot be changed again"
            )

        hr_user = users[DEMO_HR_BY_EMPLOYER[spec["employer"]]]

        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=hr_user)
        endpoint = "confirm" if decision == "confirmed" else "reject"
        response = client.post(
            f"/api/v1/hr/nurses/{nurse.pk}/{endpoint}/",
            {},
            HTTP_HOST="localhost",
        )
        if response.status_code != 200:
            raise CommandError(
                f"Employment {endpoint} failed for {spec['full_name']} "
                f"(HTTP {response.status_code}): "
                f"{getattr(response, 'data', response.content)}"
            )
        return f"employment {decision} via HR API ({hr_user.username})"

    def _ensure_initial_document(self, nurse, spec, supervisor):
        """Review the initial licence document the way Django admin does."""
        document = nurse.documents.filter(
            document_type=LicenceDocument.DocumentType.INITIAL
        ).first()
        if document is None:
            return
        reviewed = spec["target_status"] in {
            Nurse.RecordStatus.APPROVED,
            Nurse.RecordStatus.SUSPENDED,
            Nurse.RecordStatus.REVOKED,
        }
        document.decision = (
            LicenceDocument.Decision.APPROVED
            if reviewed
            else LicenceDocument.Decision.PENDING
        )
        document.reviewed_by = supervisor if reviewed else None
        document.reviewed_at = timezone.now() if reviewed else None
        document.save(update_fields=["decision", "reviewed_by", "reviewed_at"])

    def _ensure_renewal_document(self, nurse, spec):
        """Add the demo renewal application for the nurse closest to expiry."""
        if spec["licence_number"] != DEMO_RENEWAL_LICENCE:
            return
        LicenceDocument.objects.get_or_create(
            nurse=nurse,
            document_type=LicenceDocument.DocumentType.RENEWAL,
            defaults={
                "file": ContentFile(MINIMAL_PDF, name="demo_renewal_licence.pdf"),
                "proposed_expiry": timezone.localdate()
                + timedelta(days=spec["renewal_proposed_expiry_days"]),
                "decision": LicenceDocument.Decision.PENDING,
            },
        )

    def _ensure_nurse_account(self, nurse, spec):
        """Attach a login so the digital ID card can be demonstrated."""
        User = get_user_model()
        username = spec["nurse_account"]
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": spec["email"]},
        )
        user.email = spec["email"]
        user.set_password(DEMO_PASSWORD)
        user.save()
        nurse.user = user
        nurse.save(update_fields=["user", "updated_at"])
        self.stdout.write(
            f"  nurse account {'created' if created else 'updated'}: "
            f"{username} -> {spec['full_name']}"
        )

    # --- reset ---------------------------------------------------------------

    def _reset(self):
        User = get_user_model()
        demo_employer_names = set(DEMO_EMPLOYERS) | LEGACY_DEMO_EMPLOYERS
        demo_usernames = set(DEMO_USERS) | set(DEMO_NURSE_ACCOUNTS) | LEGACY_DEMO_USERNAMES

        demo_nurses = [
            nurse
            for nurse in Nurse.objects.select_related("employer").all()
            if nurse.licence_number.startswith(DEMO_LICENCE_PREFIX)
            or LEGACY_LICENCE_PATTERN.match(nurse.licence_number)
            or (nurse.employer and nurse.employer.name in demo_employer_names)
        ]

        removed_files = 0
        for nurse in demo_nurses:
            if nurse.photo:
                nurse.photo.delete(save=False)
                removed_files += 1
            for document in nurse.documents.all():
                if document.file:
                    document.file.delete(save=False)
                    removed_files += 1
        Nurse.objects.filter(pk__in=[nurse.pk for nurse in demo_nurses]).delete()

        employers_to_remove = Employer.objects.filter(name__in=demo_employer_names)
        users_to_remove = User.objects.filter(username__in=demo_usernames)
        employers_removed = employers_to_remove.count()
        users_removed = users_to_remove.count()
        employers_to_remove.delete()
        users_to_remove.delete()

        self.stdout.write(
            self.style.WARNING(
                f"Removed demo data: {len(demo_nurses)} nurses, "
                f"{employers_removed} employers, {users_removed} accounts, "
                f"{removed_files} uploaded files."
            )
        )

    # --- summary -------------------------------------------------------------

    def _print_summary(self):
        demo = Nurse.objects.filter(
            licence_number__startswith=DEMO_LICENCE_PREFIX
        ).select_related("employer")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Demonstration dataset ready."))
        self.stdout.write(
            "Every name, employer, email address, NIN and licence number below "
            "is fictional test data."
        )
        self.stdout.write("")

        for nurse in demo.order_by("licence_number"):
            self.stdout.write(
                f"  {nurse.licence_number}  {nurse.full_name:<20} "
                f"{nurse.record_status:<9} {nurse.employment_status:<10} "
                f"licence={nurse.public_licence_status:<14} "
                f"{nurse.employer.name if nurse.employer else '-'}"
            )

        self.stdout.write("")
        self.stdout.write(
            "Demo totals: {total} nurses | {approved} approved | {pending} pending | "
            "{rejected} rejected | {restricted} suspended/revoked | {flagged} flagged".format(
                **demo.aggregate(
                    total=Count("pk"),
                    approved=Count(
                        "pk", filter=Q(record_status=Nurse.RecordStatus.APPROVED)
                    ),
                    pending=Count(
                        "pk", filter=Q(record_status=Nurse.RecordStatus.PENDING)
                    ),
                    rejected=Count(
                        "pk", filter=Q(record_status=Nurse.RecordStatus.REJECTED)
                    ),
                    restricted=Count(
                        "pk",
                        filter=Q(record_status__in=[
                            Nurse.RecordStatus.SUSPENDED,
                            Nurse.RecordStatus.REVOKED,
                        ]),
                    ),
                    flagged=Count(
                        "pk", filter=Q(record_status=Nurse.RecordStatus.FLAGGED)
                    ),
                )
            )
        )
        self.stdout.write(
            "Demo employers: "
            f"{Employer.objects.filter(name__endswith='(Demo)').count()}"
        )
        self.stdout.write("")

        self.stdout.write(f"Demo password for every account: {DEMO_PASSWORD}")
        self.stdout.write("Admin accounts:  demo_superadmin, demo_supervisor, demo_officer1")
        self.stdout.write(
            "Hospital HR accounts:  demo_hr1, demo_hr2, demo_hr3, demo_hr4, demo_hr5"
        )
        self.stdout.write(
            "Nurse accounts (digital ID card):  "
            + ", ".join(DEMO_NURSE_ACCOUNTS)
        )
        self.stdout.write("")

        approved = demo.filter(
            record_status=Nurse.RecordStatus.APPROVED, nanm_id__isnull=False
        ).first()
        if approved:
            self.stdout.write(
                f"Public verification example: /verify/{approved.nanm_id}/"
            )
