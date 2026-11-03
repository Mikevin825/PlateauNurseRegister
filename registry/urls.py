from django.urls import path

from . import views

app_name = "registry"

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path(
        "register/success/<int:pk>/",
        views.registration_success,
        name="registration_success",
    ),
    path("documents/<int:pk>/", views.protected_document, name="protected_document"),
    path(
        "nurses/<int:pk>/photo/",
        views.protected_nurse_photo,
        name="protected_nurse_photo",
    ),
    path("verify/", views.verify, name="verify"),
    path("verify/<str:nanm_id>/", views.verify_result, name="verify_result"),
    path("nurses/<int:pk>/card/", views.card, name="card"),
    path("card/<str:token>/", views.signed_card, name="signed_card"),
]
