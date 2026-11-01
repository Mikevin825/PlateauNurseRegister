import re
from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from PIL import Image, UnidentifiedImageError

from .crypto import hash_nin
from .models import Employer, Nurse

MAX_UPLOAD_SIZE = 10 * 1024 * 1024
ALLOWED_SCAN_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}
PHONE_PATTERN = re.compile(r"^\+?[0-9]{10,15}$")
NIN_PATTERN = re.compile(r"^\d{11}$")


def _validate_upload(upload, label, allow_pdf):
    if not upload:
        return upload

    extension = Path(upload.name).suffix.lower()
    allowed_extensions = ALLOWED_SCAN_EXTENSIONS if allow_pdf else ALLOWED_IMAGE_EXTENSIONS
    if extension not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise ValidationError(f"{label} must be one of: {allowed}.")

    if upload.size > MAX_UPLOAD_SIZE:
        raise ValidationError(f"{label} must be 10 MB or smaller.")

    content_type = getattr(upload, "content_type", "")
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError(f"{label} has an unsupported file type.")

    if extension == ".pdf":
        upload.seek(0)
        header = upload.read(5)
        upload.seek(0)
        if header != b"%PDF-":
            raise ValidationError(f"{label} is not a valid PDF file.")
        return upload

    try:
        image = Image.open(upload)
        image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError(f"{label} is not a valid image file.") from exc
    finally:
        upload.seek(0)

    return upload


class NurseRegistrationForm(forms.ModelForm):
    nin = forms.CharField(
        label="National Identification Number",
        min_length=11,
        max_length=11,
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "off",
                "placeholder": "11 digits",
            }
        ),
    )
    licence_scan = forms.FileField(
        label="Licence scan",
        widget=forms.ClearableFileInput(attrs={"accept": ".pdf,.jpg,.jpeg,.png"}),
    )
    selfie = forms.ImageField(
        label="Live selfie",
        widget=forms.ClearableFileInput(
            attrs={"accept": "image/jpeg,image/png", "capture": "user"}
        ),
    )
    consent = forms.BooleanField(
        label="The nurse has consented to registration and data processing.",
        error_messages={
            "required": "You must record the nurse's consent before registering."
        },
    )
    confirm_duplicate = forms.BooleanField(
        label="I have reviewed the duplicate warning and want to continue.",
        required=False,
    )

    class Meta:
        model = Nurse
        fields = (
            "full_name",
            "phone",
            "email",
            "licence_number",
            "licence_expiry",
            "specialty",
            "cadre",
            "employer",
            "ward",
        )
        widgets = {
            "licence_expiry": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["employer"].queryset = Employer.objects.all()
        self.duplicate_warning = ""

    def clean_nin(self):
        nin = (self.cleaned_data.get("nin") or "").strip()
        if not NIN_PATTERN.fullmatch(nin):
            raise ValidationError("NIN must be exactly 11 digits.")
        return nin

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not PHONE_PATTERN.fullmatch(phone):
            raise ValidationError("Enter a valid phone number with 10 to 15 digits.")
        return phone

    def clean_licence_number(self):
        licence_number = (self.cleaned_data.get("licence_number") or "").strip()
        if not licence_number:
            raise ValidationError("Licence number is required.")
        return licence_number

    def clean_licence_scan(self):
        return _validate_upload(
            self.cleaned_data.get("licence_scan"),
            "Licence scan",
            allow_pdf=True,
        )

    def clean_selfie(self):
        return _validate_upload(
            self.cleaned_data.get("selfie"),
            "Selfie",
            allow_pdf=False,
        )

    def clean(self):
        cleaned_data = super().clean()
        nin = cleaned_data.get("nin")
        licence_number = cleaned_data.get("licence_number")
        duplicate_reasons = []

        if nin and Nurse.objects.filter(nin_hash=hash_nin(nin)).exists():
            duplicate_reasons.append("NIN")

        if licence_number and Nurse.objects.filter(
            licence_number__iexact=licence_number
        ).exists():
            duplicate_reasons.append("licence number")

        if duplicate_reasons:
            self.duplicate_warning = (
                "A nurse with this "
                + " and this ".join(duplicate_reasons)
                + " already exists. Check the record before continuing."
            )
            if not cleaned_data.get("confirm_duplicate"):
                self.add_error(
                    "confirm_duplicate",
                    "This record looks like a duplicate. Confirm before continuing.",
                )

        return cleaned_data

    def save(self, commit=True):
        nurse = super().save(commit=False)
        nurse.created_by = self.user
        nurse.record_status = Nurse.RecordStatus.PENDING
        nurse.consent_at = timezone.now()
        nurse.set_nin(self.cleaned_data["nin"])
        nurse.photo = self.cleaned_data["selfie"]
        if commit:
            nurse.save()
        return nurse
