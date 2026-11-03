import mimetypes
from pathlib import Path

from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.db import transaction
from io import BytesIO

from .forms import NurseRegistrationForm
from .models import LicenceDocument, Nurse
from .permissions import (
    can_view_documents,
    can_view_nurse_photo,
    is_officer_or_above,
)


def home(request):
    return render(request, "home.html")


@login_required
def register(request):
    if not is_officer_or_above(request.user):
        raise PermissionDenied

    if request.method == "POST":
        form = NurseRegistrationForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                nurse = form.save()
                LicenceDocument.objects.create(
                    nurse=nurse,
                    file=form.cleaned_data["licence_scan"],
                    document_type=LicenceDocument.DocumentType.INITIAL,
                )
            return redirect("registry:registration_success", pk=nurse.pk)
    else:
        form = NurseRegistrationForm(user=request.user)

    return render(request, "register.html", {"form": form})


@login_required
def registration_success(request, pk):
    if not is_officer_or_above(request.user):
        raise PermissionDenied

    nurse = get_object_or_404(Nurse, pk=pk)
    return render(request, "registration_success.html", {"nurse": nurse})


@login_required
def protected_document(request, pk):
    if not can_view_documents(request.user):
        raise PermissionDenied

    document = get_object_or_404(
        LicenceDocument.objects.select_related("nurse__employer"),
        pk=pk,
    )
    return _serve_media(document.file)


@login_required
def protected_nurse_photo(request, pk):
    nurse = get_object_or_404(Nurse.objects.select_related("employer"), pk=pk)
    if not can_view_nurse_photo(request.user, nurse):
        raise PermissionDenied

    return _serve_media(nurse.photo)


def _serve_media(field_file):
    if not field_file:
        raise Http404

    try:
        path = Path(field_file.path).resolve()
    except (NotImplementedError, ValueError) as exc:
        raise Http404 from exc

    media_root = Path(settings.MEDIA_ROOT).resolve()
    if not path.is_relative_to(media_root) or not path.is_file():
        raise Http404

    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path.open("rb"), content_type=content_type)


from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def verify(request):
    """Public verification page."""
    nanm_id = request.GET.get("nanm_id", "").strip()
    if not nanm_id:
        return render(request, "verify.html")
    nurse = Nurse.objects.select_related("employer").filter(nanm_id=nanm_id).first()
    if not nurse:
        return render(request, "verify.html", {"not_registered": True})
    # Build public status using the model property
    status = nurse.public_licence_status
    # Photo URL: if photo exists, build absolute URL; otherwise use placeholder
    photo_url = ""
    if nurse.photo:
        try:
            photo_url = request.build_absolute_uri(nurse.photo.url)
        except Exception:
            photo_url = ""
    ctx = {
        "nurse": nurse,
        "status": status,
        "nanm_id": nurse.nanm_id,
        "full_name": nurse.full_name,
        "licence_expiry": nurse.licence_expiry,
        "employer": nurse.employer.name if nurse.employer else "",
        "photo_url": photo_url,
    }
    return render(request, "verify.html", ctx)


def verify_result(request, nanm_id):
    """Show verification result for a given NANNM ID."""
    nurse = Nurse.objects.select_related("employer").filter(nanm_id=nanm_id).first()
    if not nurse:
        return render(request, "verify.html", {"not_registered": True})
    # Build public status using the model property
    status = nurse.public_licence_status
    # Photo URL: if photo exists, build absolute URL; otherwise use placeholder
    photo_url = ""
    if nurse.photo:
        try:
            photo_url = request.build_absolute_uri(nurse.photo.url)
        except Exception:
            photo_url = ""
    ctx = {
        "nurse": nurse,
        "status": status,
        "nanm_id": nurse.nanm_id,
        "full_name": nurse.full_name,
        "licence_expiry": nurse.licence_expiry,
        "employer": nurse.employer.name if nurse.employer else "",
        "photo_url": photo_url,
    }
    return render(request, "verify.html", ctx)


@login_required
def card(request, pk):
    nurse = get_object_or_404(Nurse, pk=pk)
    # generate signed link
    token = signing.dumps({"nurse_id": nurse.pk}, salt=settings.CARD_LINK_SALT)
    signed_url = request.build_absolute_uri(reverse("registry:signed_card", args=[token]))
    # direct URL (requires login)
    direct_url = reverse("registry:card", args=[pk])
    ctx = {
        "nurse": nurse,
        "signed_url": signed_url,
        "direct_url": direct_url,
    }
    return render(request, "card.html", ctx)


def signed_card(request, token):
    try:
        data = signing.loads(token, salt=settings.CARD_LINK_SALT, max_age=settings.CARD_LINK_MAX_AGE)
        nurse_id = data["nurse_id"]
        nurse = get_object_or_404(Nurse, pk=nurse_id)
        # render same card view without login requirement
        ctx = {
            "nurse": nurse,
            "signed": True,
        }
        return render(request, "card.html", ctx)
    except Exception:
        return render(request, "card_invalid.html", status=400)
