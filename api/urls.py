from django.urls import path

from .views import verify_nurse

urlpatterns = [
    path("verify/<str:nanm_id>/", verify_nurse, name="verify_nurse"),
]
