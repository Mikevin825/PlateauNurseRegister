from django.core.exceptions import PermissionDenied

from .permissions import can_reveal_nin


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
