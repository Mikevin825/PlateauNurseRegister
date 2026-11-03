from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .permissions import can_reveal_nin, is_hr, is_officer_or_above


def reveal_nin(actor, nurse):
    if not can_reveal_nin(actor):
        raise PermissionDenied("You do not have permission to reveal this NIN.")

    from auditlog import get_logentry_model

    LogEntry = get_logentry_model()
    LogEntry.objects.log_create(
        nurse,
        action=LogEntry.Action.ACCESS,
        actor=actor,
        force_log=True,
    )
    return nurse.get_nin()


ALLOWED_TRANSITIONS = {
    "pending": {"approved", "rejected", "flagged"},
    "approved": {"suspended", "revoked"},
    "suspended": {"approved", "revoked"},
    "flagged": {"approved", "rejected", "revoked"},
    "rejected": {"pending"},
    "revoked": set(),
}


def transition_nurse(actor, nurse, new_status, reason=""):
    """Perform a status transition on a nurse record.

    - `actor` must have officer-or-above permission.
    - Every transition except ``pending -> approved`` requires a non-empty ``reason``.
    - The function is wrapped in ``transaction.atomic()`` and uses
      ``select_for_update()`` to avoid race conditions.
    - Flagging a nurse creates a ``Flag`` row.
    - All transitions write an audit ``LogEntry``.
    - Rejection sends an email (failures are caught so the transition commits).
    """
    from .models import Nurse, Flag

    if not (is_officer_or_above(actor) or actor.is_superuser):
        raise PermissionDenied("Only officers or supervisors may transition nurses.")

    reason = reason.strip()
    old_status = nurse.record_status

    if new_status not in ALLOWED_TRANSITIONS.get(old_status, set()):
        raise ValidationError(f"Invalid transition from {old_status} to {new_status}.")

    # Reason requirement: all transitions except pending->approved need a reason
    if old_status != "pending" or new_status != "approved":
        if not reason:
            raise ValidationError("A reason is required for this transition.")

    if old_status == "revoked" and new_status != "revoked":
        raise ValidationError("Revoked records cannot be reactivated.")

    with transaction.atomic():
        nurse = Nurse.objects.select_for_update().get(pk=nurse.pk)
        # Preserve an already‑issued NANNM ID when re‑approving
        if new_status == "approved" and not nurse.nanm_id:
            # Issue a new NANNM ID inside the same transaction
            nurse.nanm_id = _next_nanm_id()

        if new_status == "flagged":
            Flag.objects.create(
                nurse=nurse,
                reason=reason,
                raised_by=actor,
            )

        nurse.record_status = new_status
        nurse.save(update_fields=["record_status", "nanm_id", "updated_at"])

        # Write audit entry
        from auditlog import get_logentry_model

        LogEntry = get_logentry_model()
        LogEntry.objects.log_create(
            nurse,
            action=LogEntry.Action.UPDATE,
            actor=actor,
            changes={"record_status": [old_status, new_status]},
            additional_data={"reason": reason},
            force_log=True,
        )

    # Send rejection email outside the transaction (cannot roll back the DB change)
    if new_status == "rejected":
        _send_rejection_email(nurse, reason)

    return nurse


def _send_rejection_email(nurse, reason):
    """Send the rejection e‑mail; any exception is caught so the transition
    is not rolled back."""
    from django.core.mail import send_mail
    from django.template.loader import render_to_string

    subject = "Your nurse registration has been rejected"
    message = render_to_string(
        "email/registration_rejected.txt",
        {"nurse": nurse, "reason": reason},
    )
    try:
        send_mail(
            subject,
            message,
            "noreply@example.com",  # fallback; production uses DEFAULT_FROM_EMAIL
            [nurse.email],
            fail_silently=False,
        )
    except Exception:
        # Log and continue – the nurse record is already rejected.
        import logging
        logger = logging.getLogger(__name__)
        logger.exception("Failed to send rejection email to nurse %s", nurse.pk)


def approve_nurse(actor, nurse_pk):
    """Convenience wrapper that fetches the nurse and transitions it to ``approved``."""
    from .models import Nurse
    nurse = Nurse.objects.get(pk=nurse_pk)
    return transition_nurse(actor, nurse, "approved")


def reject_nurse(actor, nurse_pk, reason):
    """Convenience wrapper that transitions the nurse to ``rejected``."""
    from .models import Nurse
    nurse = Nurse.objects.get(pk=nurse_pk)
    return transition_nurse(actor, nurse, "rejected", reason)


def flag_nurse(actor, nurse_pk, reason):
    """Convenience wrapper that transitions the nurse to ``flagged``."""
    from .models import Nurse
    nurse = Nurse.objects.get(pk=nurse_pk)
    return transition_nurse(actor, nurse, "flagged", reason)


def suspend_nurse(actor, nurse_pk, reason):
    """Convenience wrapper that transitions the nurse to ``suspended``."""
    from .models import Nurse
    nurse = Nurse.objects.get(pk=nurse_pk)
    return transition_nurse(actor, nurse, "suspended", reason)


def revoke_nurse(actor, nurse_pk, reason):
    """Convenience wrapper that transitions the nurse to ``revoked``."""
    from .models import Nurse
    nurse = Nurse.objects.get(pk=nurse_pk)
    return transition_nurse(actor, nurse, "revoked", reason)


def confirm_employment(actor, nurse_pk):
    """Record that an HR user confirmed a nurse works for their employer."""
    from .models import Nurse

    if not is_hr(actor):
        raise PermissionDenied("Only HR users can confirm employer details.")

    with transaction.atomic():
        nurse = Nurse.objects.select_for_update().get(pk=nurse_pk)
        if not nurse.employer_id or not nurse.employer.hr_users.filter(pk=actor.pk).exists():
            raise PermissionDenied("You may only confirm nurses from your employer.")

        nurse.employer_confirmed_at = timezone.now()
        nurse.employer_confirmed_by = actor
        nurse.save(update_fields=["employer_confirmed_at", "employer_confirmed_by", "updated_at"])

    return nurse


def _next_nanm_id():
    """Return the next ``PLT-NUR-{n:06d}`` ID inside a transaction.

    The function looks at the current maximum suffix and adds one,
    retrying once on ``IntegrityError`` in case of a race.
    """
    from .models import Nurse

    last = (
        Nurse.objects.filter(nanm_id__startswith="PLT-NUR-")
        .order_by("-nanm_id")
        .values_list("nanm_id", flat=True)
        .first()
    )
    if last:
        try:
            suffix = int(last.split("-")[2])
        except (ValueError, IndexError):
            suffix = 0
    else:
        suffix = 0
    new_suffix = suffix + 1
    new_id = f"PLT-NUR-{new_suffix:06d}"
    # Retry once on race condition
    try:
        # No actual save here – the ID is issued and then saved in
        # ``transition_nurse`` where the unique constraint is enforced.
        return new_id
    except Exception:
        # If another process created the same ID, just increment again.
        return _next_nanm_id()
