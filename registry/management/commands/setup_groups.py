from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from registry.permissions import ALL_GROUPS, HR, OFFICER, SUPER_ADMIN, SUPERVISOR


class Command(BaseCommand):
    help = "Create registry groups and assign their permissions."

    def handle(self, *args, **options):
        registry_permissions = Permission.objects.filter(content_type__app_label="registry")
        auditlog_permissions = Permission.objects.filter(content_type__app_label="auditlog")

        officer_codenames = {
            "view_nurse",
            "add_nurse",
            "change_nurse",
            "view_licencedocument",
            "add_licencedocument",
            "view_employer",
            "view_flag",
            "add_flag",
            "view_notification",
        }
        supervisor_codenames = officer_codenames | {
            "change_licencedocument",
            "change_flag",
            "delete_flag",
        }
        hr_codenames = {"view_nurse", "view_employer"}

        assignments = {
            OFFICER: registry_permissions.filter(codename__in=officer_codenames),
            SUPERVISOR: registry_permissions.filter(codename__in=supervisor_codenames),
            SUPER_ADMIN: registry_permissions | auditlog_permissions,
            HR: registry_permissions.filter(codename__in=hr_codenames),
        }

        for group_name in ALL_GROUPS:
            group, _ = Group.objects.get_or_create(name=group_name)
            group.permissions.set(assignments[group_name])
            self.stdout.write(self.style.SUCCESS(f"{group_name}: permissions updated"))

        self.stdout.write(self.style.SUCCESS("Registry groups are ready."))
