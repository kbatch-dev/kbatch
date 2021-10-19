from django.urls import include, path
from django.contrib import admin
from rest_framework import routers
from django_kbatch_server import views


router = routers.DefaultRouter()
router.register(r"users", views.UserViewSet)
router.register(r"groups", views.GroupViewSet)
router.register(r"jobs", views.JobViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path(r"services/kbatch/", include(router.urls)),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("admin/", admin.site.urls),
]
