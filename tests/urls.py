###############
# Qiyas Sadıqov CC
###############

from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path


def page(request):
    return HttpResponse(
        "<html><head><title>Test</title></head><body><h1>Hi</h1></body></html>",
        content_type="text/html",
    )


urlpatterns = [
    path("admin/", admin.site.urls),
    path("sightline/", include("sightline.urls")),
    path("", page, name="home"),
    path("shop/", page, name="shop"),
]
