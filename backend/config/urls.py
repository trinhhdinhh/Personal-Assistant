from django.contrib import admin
from django.urls import path

from agent import views as agent_views
from data import views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/report", views.report),
    path("api/forecast", agent_views.forecast),
    path("api/brief", agent_views.brief),
    path("api/chat", agent_views.chat),  # POST, runs the agent
    path("api/suggestions", agent_views.save_suggestion),  # POST, the user added a suggestion
    path("api/events", views.add_event),  # POST, the user adds an event on the Week page
    path("api/events/<int:event_id>", views.change_event),  # PUT edits it, DELETE removes it
]
