from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import DetailView, ListView, TemplateView

from league.models import Game, Player
from .forms import GameEventCreateForm, GameCreateForm
from .models import GameEvent, PlayerGameStat, TeamGameStat


class LiveHomeView(TemplateView):
    template_name = "live/home.html"

    @method_decorator(staff_member_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


@method_decorator(staff_member_required, name="dispatch")
class LiveGameListView(ListView):
    model = Game
    template_name = "live/game_list.html"
    context_object_name = "games"
    paginate_by = 30

    def get_queryset(self):
        return Game.objects.select_related("home_team", "away_team").order_by("-start_at", "-id")

    def post(self, request, *args, **kwargs):
        form = GameCreateForm(request.POST)
        if form.is_valid():
            game = form.save(commit=False)
            game.status = Game.Status.SCHEDULED
            game.current_period = 1
            game.clock_seconds = game.period_duration
            game.clock_running = False
            game.clock_updated_at = timezone.now()
            game.save()
            return redirect("live:game_detail", pk=game.pk)
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        context["create_form"] = form
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.setdefault("create_form", GameCreateForm())
        return ctx


@method_decorator(staff_member_required, name="dispatch")
class LiveGameDetailView(DetailView):
    model = Game
    template_name = "live/game_detail.html"
    context_object_name = "game"

    def get_queryset(self):
        return Game.objects.select_related("home_team", "away_team")

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        game: Game = self.object
        # пересчитываем текущее время по серверу
        game_seconds = self._effective_seconds(game)
        action = (request.POST.get("action") or "").strip()
        if action:
            if action == "start_game":
                game.status = Game.Status.LIVE
                game.current_period = 1
                game.clock_running = False
                game.clock_seconds = game.period_duration
                game.clock_updated_at = timezone.now()
            elif action == "clock_start":
                game.clock_running = True
                game.clock_seconds = game_seconds
                game.clock_updated_at = timezone.now()
            elif action == "clock_stop":
                game.clock_running = False
                game.clock_seconds = game_seconds
                game.clock_updated_at = timezone.now()
            elif action == "clock_reset":
                game.clock_running = False
                game.clock_seconds = game.period_duration
                game.clock_updated_at = timezone.now()
            elif action == "period_next":
                game.current_period += 1
                game.clock_running = False
                game.clock_seconds = game.period_duration
                game.clock_updated_at = timezone.now()
            elif action == "period_prev" and game.current_period > 1:
                game.current_period -= 1
                game.clock_running = False
                game.clock_seconds = game.period_duration
                game.clock_updated_at = timezone.now()
            elif action == "finish_game":
                game.status = Game.Status.FINISHED
                game.clock_running = False
                game.clock_seconds = 0
                game.clock_updated_at = timezone.now()
            game.save(update_fields=["status", "clock_running", "clock_seconds", "current_period", "clock_updated_at"])
            return redirect("live:game_detail", pk=game.pk)
        data = request.POST.copy()
        quick_type = (data.get("quick_type") or "").strip()
        form = GameEventCreateForm(data, game=game)
        if not quick_type:
            ctx = self.get_context_data()
            ctx["form"] = form
            ctx["event_type_error"] = True
            return self.render_to_response(ctx)
        if form.is_valid():
            event = form.save(commit=False)
            event.game = game
            event.event_type = quick_type
            event.period = game.current_period
            event.clock_seconds = game_seconds
            last_seq = (
                GameEvent.objects.filter(game=game)
                .order_by("-sequence", "-id")
                .values_list("sequence", flat=True)
                .first()
                or 0
            )
            event.sequence = last_seq + 1
            event.save()
            return redirect("live:game_detail", pk=game.pk)
        ctx = self.get_context_data()
        ctx["form"] = form
        return self.render_to_response(ctx)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        game: Game = ctx["game"]
        clock_seconds = self._effective_seconds(game)
        ctx["form"] = GameEventCreateForm(
            game=game,
            initial={
                "team": game.home_team,
            },
        )
        ctx["quick_types"] = [
            ("fg2_made", "2 очка +"),
            ("fg2_miss", "2 очка −"),
            ("ft_made", "Штрафной +"),
            ("ft_miss", "Штрафной −"),
            ("assist", "Ассист"),
            ("reb_o", "Подбор (нап)"),
            ("reb_d", "Подбор (защ)"),
            ("steal", "Перехват"),
            ("turnover", "Потеря"),
            ("block", "Блок"),
            ("foul", "Фол"),
            ("foul_drawn", "Фол соп"),
        ]
        ctx["events"] = (
            GameEvent.objects.filter(game=game)
            .select_related("team", "player", "related_player")
            .order_by("-period", "-clock_seconds", "-sequence", "-id")[:50]
        )
        ctx["team_stats"] = {s.team_id: s for s in TeamGameStat.objects.filter(game=game)}
        ctx["player_stats"] = (
            PlayerGameStat.objects.filter(game=game)
            .select_related("team", "player")
            .order_by("-points", "-shots_made", "player__last_name", "player__first_name")
        )
        ctx["clock_seconds"] = clock_seconds
        ctx["players_for_game"] = (
            Player.objects.filter(team__in=[game.home_team, game.away_team], is_active=True)
            .select_related("team")
            .order_by("team__name", "last_name", "first_name")
        )
        return ctx

    def _effective_seconds(self, game: Game) -> int:
        seconds = int(game.clock_seconds)
        if game.clock_running and game.clock_updated_at:
            delta = timezone.now() - game.clock_updated_at
            passed = int(delta.total_seconds())
            seconds = max(0, seconds - passed)
        return seconds

