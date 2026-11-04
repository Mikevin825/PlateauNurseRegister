from datetime import timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from PIL import Image

from registry.models import Employer, Flag, LicenceDocument, Notification, Nurse
from registry.permissions import HR, OFFICER, SUPER_ADMIN, SUPERVISOR

DEMO_PASSWORD = "DemoPass123!"
DEMO_USERNAMES = {
    "demo_superadmin",
    "demo_officer1",
    "demo_officer2",
    "demo_supervisor",
    "demo_hr1",
    "demo_hr2",
    "demo_nurse",
}
DEMO_ADMIN_USERNAMES = [
    "demo_officer1",
    "demo_officer2",
    "demo_supervisor",
    "demo_hr1",
    "demo_hr2",
]
DEMO_EMPLOYERS = {
    "Plateau Specialist Hospital": ("hospital", "Jos North"),
    "Bingham University Teaching Hospital": ("hospital", "Jos North"),
    "Jos South Comprehensive Health Centre": ("primary_health_centre", "Jos South"),
    "Vom Christian Clinic": ("clinic", "Jos South"),
}
FIRST_NAMES = [
    "Amina",
    "Grace",
    "Blessing",
    "Esther",
    "Mary",
    "Joy",
    "Hauwa",
    "Ruth",
    "Deborah",
    "Lydia",
    "Naomi",
    "Rebecca",
    "Sarah",
    "Martha",
    "Priscilla",
    "Comfort",
    "Faith",
    "Hope",
    "Gloria",
    "Patience",
]
LAST_NAMES = [
    "Adamu",
    "Bala",
    "Chukwu",
    "Danjuma",
    "Eze",
    "Garba",
    "Ibrahim",
    "James",
    "Kalu",
    "Musa",
    "Nwosu",
    "Okafor",
    "Pam",
    "Rwang",
    "Sani",
    "Terna",
    "Uche",
    "Wuyep",
    "Yakubu",
    "Zamani",
]
SPECIALTIES = [
    "General Nursing",
    "Midwifery",
    "Community Health",
    "Paediatric Nursing",
    "Mental Health",
]
CADRES = ["Nurse", "Midwife", "Nurse/Midwife"]
PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
    b"trailer\n<< /Root 1 0 R >>\n%%EOF\n"
)


def _image_bytes(color):
    buffer = BytesIO()
    Image.new("RGB", (240, 240), color).save(buffer, format="JPEG")
    return buffer.getvalue()


class Command(BaseCommand):
    help = "Create repeatable demo registry data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing demo data before seeding.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        has_data = (
            Nurse.objects.exists()
            or Employer.objects.exists()
            or User.objects.filter(username__in=DEMO_USERNAMES).exists()
        )

        if has_data and not options["reset"]:
            raise CommandError(
                "The registry already contains data. Use --reset to replace demo data."
            )

        if options["reset"]:
            self._reset(User)

        call_command("setup_groups", stdout=self.stdout)

        employers = self._create_employers()
        users = self._create_users(User, employers)
        self._create_nurses(employers, users)

        self.stdout.write(self.style.SUCCESS("Demo data created."))
        self.stdout.write("")
        self.stdout.write("Demo admin accounts (excluding superadmin):")
        for username in DEMO_ADMIN_USERNAMES:
            self.stdout.write(f"  {username} / {DEMO_PASSWORD}")
        self.stdout.write("")
        self.stdout.write(f"Superadmin: demo_superadmin / {DEMO_PASSWORD}")
        self.stdout.write(f"Nurse: demo_nurse / {DEMO_PASSWORD}")
        self.stdout.write("")
        self.stdout.write(
            f"Nurses: {Nurse.objects.count()} | Employers: {Employer.objects.count()}"
        )

    def _reset(self, User):
        demo_nurses = Nurse.objects.filter(employer__name__in=DEMO_EMPLOYERS)
        for nurse in demo_nurses:
            if nurse.photo:
                nurse.photo.delete(save=False)
            for document in nurse.documents.all():
                if document.file:
                    document.file.delete(save=False)
        demo_nurses.delete()
        Employer.objects.filter(name__in=DEMO_EMPLOYERS).delete()
        User.objects.filter(username__in=DEMO_USERNAMES).delete()
        self.stdout.write(self.style.WARNING("Existing demo data deleted."))

    def _create_employers(self):
        employers = {}
        for name, (employer_type, lga) in DEMO_EMPLOYERS.items():
            employers[name] = Employer.objects.create(
                name=name,
                type=employer_type,
                lga=lga,
                contact_email=f"{name.split()[0].lower()}@example.test",
                approved=True,
            )
        return employers

    def _create_users(self, User, employers):
        super_admin = User.objects.create_superuser(
            username="demo_superadmin",
            email="superadmin@example.test",
            password=DEMO_PASSWORD,
        )
        officer1 = User.objects.create_user(
            username="demo_officer1",
            email="officer1@example.test",
            password=DEMO_PASSWORD,
            is_staff=True,
        )
        officer2 = User.objects.create_user(
            username="demo_officer2",
            email="officer2@example.test",
            password=DEMO_PASSWORD,
            is_staff=True,
        )
        supervisor = User.objects.create_user(
            username="demo_supervisor",
            email="supervisor@example.test",
            password=DEMO_PASSWORD,
            is_staff=True,
        )
        hr1 = User.objects.create_user(
            username="demo_hr1",
            email="hr1@example.test",
            password=DEMO_PASSWORD,
        )
        hr2 = User.objects.create_user(
            username="demo_hr2",
            email="hr2@example.test",
            password=DEMO_PASSWORD,
        )
        nurse_user = User.objects.create_user(
            username="demo_nurse",
            email="demo.nurse@example.test",
            password=DEMO_PASSWORD,
        )

        super_admin.groups.add(Group.objects.get(name=SUPER_ADMIN))
        officer1.groups.add(Group.objects.get(name=OFFICER))
        officer2.groups.add(Group.objects.get(name=OFFICER))
        supervisor.groups.add(Group.objects.get(name=SUPERVISOR))
        hr1.groups.add(Group.objects.get(name=HR))
        hr2.groups.add(Group.objects.get(name=HR))

        employers["Plateau Specialist Hospital"].hr_users.add(hr1)
        employers["Bingham University Teaching Hospital"].hr_users.add(hr2)

        return {
            "super_admin": super_admin,
            "officer1": officer1,
            "officer2": officer2,
            "supervisor": supervisor,
            "hr1": hr1,
            "hr2": hr2,
            "nurse": nurse_user,
        }

    def _create_nurses(self, employers, users):
        today = timezone.localdate()
        employer_list = list(employers.values())
        officer = users["officer1"]
        supervisor = users["supervisor"]

        for index in range(60):
            status, expiry = self._status_and_expiry(index, today)
            nanm_id = None
            if status in {
                Nurse.RecordStatus.APPROVED,
                Nurse.RecordStatus.SUSPENDED,
                Nurse.RecordStatus.REVOKED,
            }:
                nanm_id = f"PLT-NUR-{index + 1:06d}"

            nurse = Nurse(
                nanm_id=nanm_id,
                full_name=(
                    f"{FIRST_NAMES[index % len(FIRST_NAMES)]} "
                    f"{LAST_NAMES[(index * 3) % len(LAST_NAMES)]}"
                ),
                user=users["nurse"] if index == 0 else None,
                phone=f"0803{index + 1:07d}",
                email=f"nurse{index + 1}@example.test",
                licence_number=f"PLT-LIC-{index + 1:05d}",
                licence_expiry=expiry,
                specialty=SPECIALTIES[index % len(SPECIALTIES)],
                cadre=CADRES[index % len(CADRES)],
                employer=employer_list[index % len(employer_list)],
                ward=f"Ward {index % 8 + 1}",
                record_status=status,
                consent_at=timezone.now() - timedelta(days=index + 1),
                created_by=officer,
                employer_confirmed_at=(
                    timezone.now() - timedelta(days=index)
                    if status
                    in {
                        Nurse.RecordStatus.APPROVED,
                        Nurse.RecordStatus.SUSPENDED,
                        Nurse.RecordStatus.REVOKED,
                    }
                    else None
                ),
                employer_confirmed_by=(
                    users["hr1"] if index % 2 == 0 else users["hr2"]
                )
                if status == Nurse.RecordStatus.APPROVED
                else None,
            )
            nurse.set_nin(f"10{index + 1:09d}")
            nurse.save()
            nurse.photo.save(
                f"selfie_{index + 1}.jpg",
                ContentFile(_image_bytes(((40 + index * 3) % 255, 120, 180))),
                save=True,
            )

            decision = (
                LicenceDocument.Decision.APPROVED
                if status
                in {
                    Nurse.RecordStatus.APPROVED,
                    Nurse.RecordStatus.SUSPENDED,
                    Nurse.RecordStatus.REVOKED,
                }
                else LicenceDocument.Decision.PENDING
            )
            document = LicenceDocument(
                nurse=nurse,
                document_type=LicenceDocument.DocumentType.INITIAL,
                decision=decision,
                reviewed_by=supervisor if decision == LicenceDocument.Decision.APPROVED else None,
                reviewed_at=timezone.now() if decision == LicenceDocument.Decision.APPROVED else None,
            )
            document.file.save(
                f"licence_{index + 1}.pdf",
                ContentFile(PDF_BYTES),
                save=True,
            )

            if status in {
                Nurse.RecordStatus.FLAGGED,
                Nurse.RecordStatus.SUSPENDED,
                Nurse.RecordStatus.REVOKED,
            }:
                Flag.objects.create(
                    nurse=nurse,
                    reason=f"Demo flag for {status} record.",
                    raised_by=officer,
                )

            if status == Nurse.RecordStatus.APPROVED and expiry <= today + timedelta(days=180):
                Notification.objects.create(
                    nurse=nurse,
                    type=Notification.Type.EXPIRY_REMINDER,
                    licence_expiry=expiry,
                    status=Notification.Status.PENDING,
                )

    def _status_and_expiry(self, index, today):
        if index < 30:
            return Nurse.RecordStatus.APPROVED, today + timedelta(days=365)
        if index < 40:
            return Nurse.RecordStatus.APPROVED, today + timedelta(days=90)
        if index < 45:
            return Nurse.RecordStatus.APPROVED, today - timedelta(days=30)
        if index < 50:
            return Nurse.RecordStatus.PENDING, today + timedelta(days=180)
        if index < 55:
            return Nurse.RecordStatus.FLAGGED, today + timedelta(days=180)
        if index < 58:
            return Nurse.RecordStatus.SUSPENDED, today + timedelta(days=180)
        return Nurse.RecordStatus.REVOKED, today + timedelta(days=180)
