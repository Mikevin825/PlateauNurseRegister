from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from registry.models import Nurse

from .serializers import PublicNurseSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def verify_nurse(request, nanm_id):
    try:
        nurse = Nurse.objects.select_related("employer").get(nanm_id=nanm_id)
    except Nurse.DoesNotExist as exc:
        raise NotFound({"detail": "Not registered"}) from exc
    serializer = PublicNurseSerializer(nurse, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)
