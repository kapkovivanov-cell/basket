from __future__ import annotations

from django import forms

from league.models import Game, Player, Team, Season
from .models import GameEvent


class GameEventCreateForm(forms.ModelForm):
    class Meta:
        model = GameEvent
        fields = [
            "team",
            "player",
            "related_player",
            "note",
        ]

    def __init__(self, *args, game: Game | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        if game is not None:
            team_qs = Team.objects.filter(id__in=[game.home_team_id, game.away_team_id]).order_by("name")
            self.fields["team"].queryset = team_qs
            player_qs = Player.objects.filter(team_id__in=[game.home_team_id, game.away_team_id]).order_by(
                "last_name", "first_name"
            )
            self.fields["player"].queryset = player_qs
            self.fields["related_player"].queryset = player_qs

        for f in self.fields.values():
            if isinstance(f.widget, (forms.TextInput, forms.NumberInput, forms.Select, forms.Textarea)):
                css = f.widget.attrs.get("class", "")
                f.widget.attrs["class"] = (css + " input").strip()


class GameCreateForm(forms.ModelForm):
    class Meta:
        model = Game
        fields = [
            "season",
            "home_team",
            "away_team",
            "start_at",
            "venue",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["season"].queryset = Season.objects.order_by("-is_active", "-id")
        self.fields["start_at"].widget.input_type = "datetime-local"
        for f in self.fields.values():
            if isinstance(f.widget, (forms.TextInput, forms.NumberInput, forms.Select, forms.Textarea)):
                css = f.widget.attrs.get("class", "")
                f.widget.attrs["class"] = (css + " input").strip()

    def clean(self):
        cleaned = super().clean()
        home = cleaned.get("home_team")
        away = cleaned.get("away_team")
        if home and away and home == away:
            self.add_error("away_team", "Команды должны быть разными.")
        return cleaned

