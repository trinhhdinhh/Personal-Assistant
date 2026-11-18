from django.contrib import admin
from django.urls import path

from agent import views as agent_views
from data import views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/report", views.report),
    path("api/forecast", views.forecast),
    path("api/brief", views.brief),
    path("api/chat", agent_views.chat),  # POST, runs the agent
]
