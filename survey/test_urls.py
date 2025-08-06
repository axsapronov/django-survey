# pylint: disable=invalid-name


from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include
from django.urls import path
from django.urls import re_path
from django.urls.base import reverse


def home(request):
    """Permit to not get 404 while testing."""
    return redirect(reverse("survey:survey-list"))


urlpatterns = [
    path("", home, name="home"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("survey/", include("survey.urls")),
    re_path(r"^admin/", admin.site.urls),
]
