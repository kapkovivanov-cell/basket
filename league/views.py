from django.db.models import Count, F, Prefetch, Sum
from django.views.generic import DetailView, ListView, TemplateView

from .models import Game, Player, Team
from live.models import GameEvent, PlayerGameStat, TeamGameStat


class HomeView(TemplateView):
    template_name = "league/home.html"


class TeamListView(ListView):
    model = Team
    template_name = "league/team_list.html"
    context_object_name = "teams"
    paginate_by = 24

    def get_queryset(self):
        return Team.objects.order_by("name")


class TeamDetailView(DetailView):
    model = Team
    template_name = "league/team_detail.html"
    context_object_name = "team"

    def get_queryset(self):
        return Team.objects.prefetch_related(
            Prefetch("players", queryset=Player.objects.order_by("last_name", "first_name"))
        )


class PlayerListView(ListView):
    model = Player
    template_name = "league/player_list.html"
    context_object_name = "players"
    paginate_by = 48

    def get_queryset(self):
        qs = Player.objects.select_related("team").order_by("last_name", "first_name")
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(search_name__icontains=q)
        return qs


class PlayerDetailView(DetailView):
    model = Player
    template_name = "league/player_detail.html"
    context_object_name = "player"

    def get_queryset(self):
        return Player.objects.select_related("team")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        player: Player = ctx["player"]
        totals = PlayerGameStat.objects.filter(player=player).aggregate(
            games=Count("id"),
            points=Sum("points"),
            assists=Sum("assists"),
            rebounds_off=Sum("rebounds_off"),
            rebounds_def=Sum("rebounds_def"),
            steals=Sum("steals"),
            turnovers=Sum("turnovers"),
            blocks=Sum("blocks"),
            fouls=Sum("fouls"),
            fouls_against=Sum("fouls_against"),
            shots_att=Sum("shots_att"),
            shots_made=Sum("shots_made"),
            fg2_att=Sum("fg2_att"),
            fg2_made=Sum("fg2_made"),
            ft_att=Sum("ft_att"),
            ft_made=Sum("ft_made"),
        )
        ctx["games_count"] = int(totals.get("games") or 0)
        ctx["totals"] = {k: int(v or 0) for k, v in totals.items() if k != "games"}
        ctx["recent_games"] = (
            PlayerGameStat.objects.filter(player=player)
            .select_related("game", "game__home_team", "game__away_team")
            .order_by("-game__start_at", "-game_id")[:10]
        )
        return ctx


class GameListView(ListView):
    model = Game
    template_name = "league/game_list.html"
    context_object_name = "games"
    paginate_by = 30

    def get_queryset(self):
        return (
            Game.objects.select_related("home_team", "away_team")
            .order_by("-start_at", "-id")
        )


class GameDetailView(DetailView):
    model = Game
    template_name = "league/game_detail.html"
    context_object_name = "game"

    def get_queryset(self):
        return Game.objects.select_related("home_team", "away_team")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        game: Game = ctx["game"]
        ctx["team_stats"] = {s.team_id: s for s in TeamGameStat.objects.filter(game=game)}
        ctx["player_stats"] = (
            PlayerGameStat.objects.filter(game=game)
            .select_related("team", "player")
            .order_by("-points", "-shots_made", "player__last_name", "player__first_name")
        )
        ctx["events"] = (
            GameEvent.objects.filter(game=game)
            .select_related("team", "player", "related_player")
            .order_by("-period", "clock_seconds", "-sequence", "-id")[:30]
        )
        return ctx


class LeadersView(TemplateView):
    template_name = "league/leaders.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = (
            Player.objects.select_related("team")
            .annotate(
                total_points=Sum("game_stats__points"),
                total_assists=Sum("game_stats__assists"),
                total_reb_o=Sum("game_stats__rebounds_off"),
                total_reb_d=Sum("game_stats__rebounds_def"),
                total_steals=Sum("game_stats__steals"),
                total_blocks=Sum("game_stats__blocks"),
            )
            .filter(total_points__isnull=False)
        )
        ctx["top_points"] = base.order_by("-total_points", "last_name", "first_name")[:15]
        ctx["top_assists"] = base.order_by("-total_assists", "last_name", "first_name")[:15]
        ctx["top_rebounds"] = (
            Player.objects.select_related("team")
            .annotate(
                total_reb_o=Sum("game_stats__rebounds_off"),
                total_reb_d=Sum("game_stats__rebounds_def"),
            )
            .annotate(total_reb=F("total_reb_o") + F("total_reb_d"))
            .filter(total_reb__isnull=False)
            .order_by("-total_reb", "last_name", "first_name")[:15]
        )
        ctx["top_steals"] = base.order_by("-total_steals", "last_name", "first_name")[:15]
        ctx["top_blocks"] = base.order_by("-total_blocks", "last_name", "first_name")[:15]
        return ctx

