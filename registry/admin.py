from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Employer, Flag, LicenceDocument, Notification, Nurse


class LicenceDocumentInline(admin.TabularInline):
    model = LicenceDocument
    extra = 0
    readonly_fields = ("uploaded_at", "reviewed_at", "preview")
    fields = (
        "file",
        "document_type",
        "decision",
        "reason",
        "reviewed_by",
        "reviewed_at",
        "uploaded_at",
        "preview",
    )

    @admin.display(description="Preview")
    def preview(self, obj):
        if not obj.pk or not obj.file:
            return "-"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">View file</a>',
            reverse("registry:protected_document", args=[obj.pk]),
        )


class FlagInline(admin.TabularInline):
    model = Flag
    extra = 0
    readonly_fields = ("raised_at",)
    fields = ("reason", "raised_by", "raised_at", "resolved_by", "resolved_at", "resolution")


@admin.register(Nurse)
class NurseAdmin(admin.ModelAdmin):
    list_display = (
        "nanm_id",
        "full_name",
        "record_status",
        "licence_expiry",
        "employer",
        "possible_duplicate",
    )
    list_filter = ("record_status", "employer", "licence_expiry")
    search_fields = ("nanm_id", "full_name", "licence_number", "phone")
    date_hierarchy = "licence_expiry"
    readonly_fields = (
        "nanm_id",
        "nin_last4",
        "record_status",
        "created_at",
        "updated_at",
        "consent_at",
        "created_by",
        "employer_confirmed_at",
        "employer_confirmed_by",
    )
    inlines = (LicenceDocumentInline, FlagInline)
    fieldsets = (
        (
            "Identity",
            {
                "fields": (
                    "nanm_id",
                    "full_name",
                    "phone",
                    "email",
                    "nin_last4",
                    "photo",
                )
            },
        ),
        (
            "Licence",
            {
                "fields": (
                    "licence_number",
                    "licence_expiry",
                    "specialty",
                    "cadre",
                )
            },
        ),
        (
            "Employment",
            {
                "fields": (
                    "employer",
                    "ward",
                    "employer_confirmed_at",
                    "employer_confirmed_by",
                )
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "record_status",
                    "consent_at",
                    "created_by",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    @admin.display(boolean=True, description="Possible duplicate")
    def possible_duplicate(self, obj):
        if obj.nin_hash and (
            Nurse.objects.filter(nin_hash=obj.nin_hash).exclude(pk=obj.pk).exists()
        ):
            return True
        if obj.licence_number and (
            Nurse.objects.filter(licence_number__iexact=obj.licence_number)
            .exclude(pk=obj.pk)
            .exists()
        ):
            return True
        return False


@admin.register(Employer)
class EmployerAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "lga", "approved")
    list_filter = ("type", "approved", "lga")
    search_fields = ("name", "lga", "contact_email")
    filter_horizontal = ("hr_users",)


@admin.register(LicenceDocument)
class LicenceDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "nurse",
        "document_type",
        "decision",
        "uploaded_at",
        "preview",
    )
    list_filter = ("document_type", "decision")
    search_fields = ("nurse__full_name", "nurse__nanm_id", "nurse__licence_number")
    readonly_fields = ("uploaded_at", "reviewed_at")
    raw_id_fields = ("nurse",)

    @admin.display(description="Preview")
    def preview(self, obj):
        if not obj.pk or not obj.file:
            return "-"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">View file</a>',
            reverse("registry:protected_document", args=[obj.pk]),
        )


@admin.register(Flag)
class FlagAdmin(admin.ModelAdmin):
    list_display = ("nurse", "raised_by", "raised_at", "resolved_at")
    list_filter = ("raised_at", "resolved_at")
    search_fields = ("nurse__full_name", "nurse__nanm_id", "reason")
    readonly_fields = ("raised_at",)
    raw_id_fields = ("nurse", "raised_by", "resolved_by")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("nurse", "type", "licence_expiry", "status", "sent_at")
    list_filter = ("type", "status")
    search_fields = ("nurse__full_name", "nurse__nanm_id")
    raw_id_fields = ("nurse",)
