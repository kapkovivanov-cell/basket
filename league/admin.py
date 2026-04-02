from django.contrib import admin

from .models import Game, GameRoster, Player, Season, Team


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "short_name", "city", "created_at")
    search_fields = ("name", "short_name", "city")


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("last_name", "first_name", "team", "number", "position", "is_active")
    list_filter = ("team", "is_active", "position")
    search_fields = ("last_name", "first_name")
    ordering = ("last_name", "first_name")


class GameRosterInline(admin.TabularInline):
    model = GameRoster
    extra = 0
    autocomplete_fields = ("player",)
    fields = ("team", "player", "is_starter", "is_active")


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("start_at", "season", "home_team", "away_team", "status", "venue")
    list_filter = ("season", "status", "home_team", "away_team")
    search_fields = ("venue", "home_team__name", "away_team__name")
    date_hierarchy = "start_at"
    inlines = (GameRosterInline,)

