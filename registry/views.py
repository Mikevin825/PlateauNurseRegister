import mimetypes
from pathlib import Path

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.db import transaction

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
