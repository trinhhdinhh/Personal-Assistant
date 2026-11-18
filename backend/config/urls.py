from django.contrib import admin
from django.urls import path
from data import views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/report", views.report),
    path("api/forecast", views.forecast),
    path("api/brief", views.brief),
    path("api/chat", views.chat),       # POST, runs the agent
]

