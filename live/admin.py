from django.contrib import admin

from .models import GameEvent, PlayerGameStat, TeamGameStat


@admin.register(GameEvent)
class GameEventAdmin(admin.ModelAdmin):
    list_display = ("game", "period", "clock_seconds", "sequence", "team", "player", "event_type", "related_player")
    list_filter = ("event_type", "period", "team", "game")
    search_fields = ("game__id", "player__last_name", "player__first_name", "team__name", "note")
    autocomplete_fields = ("player", "related_player")
    ordering = ("-created_at",)


@admin.register(PlayerGameStat)
class PlayerGameStatAdmin(admin.ModelAdmin):
    list_display = (
        "game",
        "team",
        "player",
        "points",
        "assists",
        "rebounds_off",
        "rebounds_def",
        "steals",
        "turnovers",
        "blocks",
        "fouls",
        "fouls_against",
        "shots_made",
        "shots_att",
        "fg2_made",
        "fg2_att",
        "ft_made",
        "ft_att",
    )
    list_filter = ("game", "team")
    search_fields = ("player__last_name", "player__first_name", "team__name")
    ordering = ("-updated_at",)


@admin.register(TeamGameStat)
class TeamGameStatAdmin(admin.ModelAdmin):
    list_display = (
        "game",
        "team",
        "points",
        "assists",
        "rebounds_off",
        "rebounds_def",
        "steals",
        "turnovers",
        "blocks",
        "fouls",
        "fouls_against",
        "shots_made",
        "shots_att",
        "fg2_made",
        "fg2_att",
        "ft_made",
        "ft_att",
    )
    list_filter = ("game", "team")
    search_fields = ("team__name",)
    ordering = ("-updated_at",)

