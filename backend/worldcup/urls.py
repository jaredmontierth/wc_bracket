from django.contrib import admin
from django.urls import include, path, re_path

from .views import frontend_app

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("brackets.urls")),
    re_path(r"^(?!static/).*", frontend_app),
]
