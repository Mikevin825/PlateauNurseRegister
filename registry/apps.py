from django.apps import AppConfig


class RegistryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "registry"

    def ready(self):
        from auditlog.registry import auditlog

        from .models import Employer, Flag, LicenceDocument, Nurse

        auditlog.register(Nurse, mask_fields=["nin_encrypted"])
        auditlog.register(Employer)
        auditlog.register(LicenceDocument)
        auditlog.register(Flag)
