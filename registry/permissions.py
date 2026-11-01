from django.db.models import QuerySet

OFFICER = "Officer"
SUPERVISOR = "Supervisor"
SUPER_ADMIN = "Super Admin"
HR = "HR"

STAFF_GROUPS = (OFFICER, SUPERVISOR, SUPER_ADMIN)
ALL_GROUPS = (OFFICER, SUPERVISOR, SUPER_ADMIN, HR)


def in_group(user, group_name):
    return bool(
        user
        and user.is_authenticated
        and user.groups.filter(name=group_name).exists()
    )


def is_officer(user):
    return in_group(user, OFFICER)


def is_supervisor(user):
    return in_group(user, SUPERVISOR)


def is_super_admin(user):
    return bool(user and user.is_authenticated and (user.is_superuser or in_group(user, SUPER_ADMIN)))


def is_hr(user):
    return in_group(user, HR)


def is_officer_or_above(user):
    return is_officer(user) or is_supervisor(user) or is_super_admin(user)


def can_reveal_nin(user):
    return is_officer_or_above(user)


def can_view_documents(user):
    return is_officer_or_above(user)


def can_view_nurse_photo(user, nurse):
    if is_officer_or_above(user):
        return True
    return bool(
        is_hr(user)
        and nurse.employer_id
        and nurse.employer.hr_users.filter(pk=user.pk).exists()
    )


def nurses_for_user(user):
    from .models import Nurse

    if is_super_admin(user) or is_supervisor(user) or is_officer(user):
        return Nurse.objects.all()
    if is_hr(user):
        return Nurse.objects.filter(employer__hr_users=user).distinct()
    return Nurse.objects.none()


def filter_employers_for_user(user, queryset: QuerySet | None = None):
    from .models import Employer

    queryset = queryset if queryset is not None else Employer.objects.all()
    if is_hr(user):
        return queryset.filter(hr_users=user).distinct()
    if is_super_admin(user) or is_supervisor(user) or is_officer(user):
        return queryset
    return queryset.none()
