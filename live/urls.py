from django.urls import path

from . import views

app_name = "live"

urlpatterns = [
    path("", views.LiveHomeView.as_view(), name="home"),
    path("games/", views.LiveGameListView.as_view(), name="game_list"),
    path("games/<int:pk>/", views.LiveGameDetailView.as_view(), name="game_detail"),
]

