from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from registry.models import Notification, Nurse


class Command(BaseCommand):
    help = "Send expiry reminder emails for nurses whose licences are near expiry."

    def handle(self, *args, **options):
        today = timezone.localdate()
        cutoff = today + timedelta(days=settings.REMINDER_DAYS)

        nurses = (
            Nurse.objects.filter(
                record_status=Nurse.RecordStatus.APPROVED,
                licence_expiry__gte=today,
                licence_expiry__lte=cutoff,
            )
            .select_related("employer")
            .order_by("licence_expiry")
        )

        sent = 0
        failed = 0
        for nurse in nurses:
            notification_key = (nurse.pk, nurse.licence_expiry)
            if Notification.objects.filter(
                nurse=nurse,
                type=Notification.Type.EXPIRY_REMINDER,
                licence_expiry=nurse.licence_expiry,
            ).exists():
                continue

            try:
                with transaction.atomic():
                    notification = Notification.objects.create(
                        nurse=nurse,
                        type=Notification.Type.EXPIRY_REMINDER,
                        licence_expiry=nurse.licence_expiry,
                        status=Notification.Status.PENDING,
                    )
                    self.send_email(nurse, notification)
                    notification.status = Notification.Status.SENT
                    notification.sent_at = timezone.now()
                    notification.save(update_fields=["status", "sent_at", "error"])
                    sent += 1
            except Exception as exc:
                failed += 1
                Notification.objects.update_or_create(
                    nurse=nurse,
                    type=Notification.Type.EXPIRY_REMINDER,
                    licence_expiry=nurse.licence_expiry,
                    defaults={
                        "status": Notification.Status.FAILED,
                        "error": str(exc),
                    },
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Expiry reminders processed: sent={sent}, failed={failed}."
            )
        )

    def send_email(self, nurse, notification):
        from django.core.mail import send_mail
        from django.template.loader import render_to_string

        message = render_to_string(
            "email/expiry_reminder.txt",
            {"nurse": nurse, "days_remaining": (nurse.licence_expiry - timezone.localdate()).days},
        )
        send_mail(
            "Nurse licence expiry reminder",
            message,
            settings.DEFAULT_FROM_EMAIL,
            [nurse.email],
            fail_silently=False,
        )
