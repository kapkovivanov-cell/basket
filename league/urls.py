from django.urls import path

from . import views

app_name = "league"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("leaders/", views.LeadersView.as_view(), name="leaders"),
    path("teams/", views.TeamListView.as_view(), name="team_list"),
    path("teams/<int:pk>/", views.TeamDetailView.as_view(), name="team_detail"),
    path("players/", views.PlayerListView.as_view(), name="player_list"),
    path("players/<int:pk>/", views.PlayerDetailView.as_view(), name="player_detail"),
    path("games/", views.GameListView.as_view(), name="game_list"),
    path("games/<int:pk>/", views.GameDetailView.as_view(), name="game_detail"),
]

