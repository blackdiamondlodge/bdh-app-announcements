from django.urls import path

from . import views

urlpatterns = [
    path("settings/buttons/", views.buttons_page, name="announcements_buttons"),
]
