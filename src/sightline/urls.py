"""
URLs.

Mount them anywhere, but keep the prefix in ``EXCLUDE_PATHS`` so the
recorder does not record itself.

    path("sightline/", include("sightline.urls")),
"""
from django.urls import path

from . import views

app_name = "sightline"

urlpatterns = [
    path("collect/", views.collect, name="collect"),
    path("panel/", views.dashboard, name="dashboard"),
    path("panel/heat/", views.heat_data, name="heat_data"),
    path("panel/visits/", views.sessions, name="sessions"),
    path("panel/replay/<uuid:session_id>/", views.replay, name="replay"),
    path("panel/replay/<uuid:session_id>/data/", views.replay_data, name="replay_data"),
]
