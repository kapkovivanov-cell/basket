from __future__ import annotations

from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from league.models import Game, Player, Team


class GameEvent(models.Model):
    class EventType(models.TextChoices):
        FG2_MADE = "fg2_made", "2 очка — попадание"
        FG2_MISS = "fg2_miss", "2 очка — промах"
        FT_MADE = "ft_made", "Штрафной — попадание"
        FT_MISS = "ft_miss", "Штрафной — промах"
        ASSIST = "assist", "Передача (ассист)"
        REB_O = "reb_o", "Подбор в нападении"
        REB_D = "reb_d", "Подбор в защите"
        STEAL = "steal", "Перехват"
        TURNOVER = "turnover", "Потеря"
        BLOCK = "block", "Блок-шот"
        FOUL = "foul", "Фол игрока"
        FOUL_DRAWN = "foul_drawn", "Фол соперника (на игроке)"

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="events", verbose_name="Матч")
    team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="events", verbose_name="Команда")
    player = models.ForeignKey(
        Player, on_delete=models.PROTECT, related_name="events", verbose_name="Игрок", blank=True, null=True
    )
    related_player = models.ForeignKey(
        Player,
        on_delete=models.PROTECT,
        related_name="related_events",
        verbose_name="Связанный игрок",
        blank=True,
        null=True,
    )
    event_type = models.CharField("Событие", max_length=20, choices=EventType.choices)
    period = models.PositiveSmallIntegerField(
        "Период",
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        default=1,
    )
    clock_seconds = models.PositiveSmallIntegerField(
        "Секунд на таймере",
        validators=[MinValueValidator(0), MaxValueValidator(60 * 15)],
        default=0,
    )
    sequence = models.PositiveIntegerField("Порядок", default=0, db_index=True)
    note = models.CharField("Примечание", max_length=200, blank=True, default="")
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "Событие матча"
        verbose_name_plural = "События матча"
        ordering = ["game_id", "period", "-clock_seconds", "sequence", "id"]
        indexes = [
            models.Index(fields=["game", "period", "clock_seconds", "sequence"]),
            models.Index(fields=["game", "team"]),
            models.Index(fields=["game", "player"]),
        ]
        constraints = []

    def __str__(self) -> str:
        p = f"{self.period}P {self.clock_seconds}s"
        who = str(self.player) if self.player_id else self.team.name
        return f"{self.game_id}: {p} {who} — {self.get_event_type_display()}"

    def clean(self):
        need_player = {
            self.EventType.FG2_MADE,
            self.EventType.FG2_MISS,
            self.EventType.FT_MADE,
            self.EventType.FT_MISS,
            self.EventType.ASSIST,
            self.EventType.REB_O,
            self.EventType.REB_D,
            self.EventType.STEAL,
            self.EventType.TURNOVER,
            self.EventType.BLOCK,
            self.EventType.FOUL,
            self.EventType.FOUL_DRAWN,
        }
        if self.event_type in need_player and self.player_id is None:
            raise ValidationError({"player": "Для этого события нужен игрок."})

        if self.player_id and self.team_id and self.player.team_id != self.team_id:
            raise ValidationError({"player": "Игрок должен принадлежать выбранной команде."})

        if self.related_player_id and self.team_id and self.related_player.team_id != self.team_id:
            raise ValidationError({"related_player": "Связанный игрок должен принадлежать выбранной команде."})

        if self.event_type == self.EventType.FG2_MADE and self.related_player_id is not None and self.related_player_id == self.player_id:
            raise ValidationError({"related_player": "Ассистент не может быть тем же игроком."})

        if self.event_type in {self.EventType.ASSIST, self.EventType.BLOCK} and self.related_player_id is not None and self.related_player_id == self.player_id:
            raise ValidationError({"related_player": "Связанный игрок не может совпадать с игроком события."})


class PlayerGameStat(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="player_stats", verbose_name="Матч")
    team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="player_stats", verbose_name="Команда")
    player = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="game_stats", verbose_name="Игрок")

    points = models.PositiveIntegerField("Очки", default=0)
    assists = models.PositiveIntegerField("Передачи", default=0)
    rebounds_off = models.PositiveIntegerField("Подборы (нап.)", default=0)
    rebounds_def = models.PositiveIntegerField("Подборы (защ.)", default=0)
    steals = models.PositiveIntegerField("Перехваты", default=0)
    turnovers = models.PositiveIntegerField("Потери", default=0)
    blocks = models.PositiveIntegerField("Блок-шоты", default=0)
    fouls = models.PositiveIntegerField("Фолы игрока", default=0)
    fouls_against = models.PositiveIntegerField("Фолы соперника", default=0)

    shots_att = models.PositiveIntegerField("Броски: попытки", default=0)
    shots_made = models.PositiveIntegerField("Броски: попадания", default=0)

    fg2_att = models.PositiveIntegerField("2 очка: попытки", default=0)
    fg2_made = models.PositiveIntegerField("2 очка: попадания", default=0)

    ft_att = models.PositiveIntegerField("Штрафные: попытки", default=0)
    ft_made = models.PositiveIntegerField("Штрафные: попадания", default=0)

    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        verbose_name = "Статистика игрока (матч)"
        verbose_name_plural = "Статистика игроков (матч)"
        constraints = [
            models.UniqueConstraint(fields=["game", "player"], name="uniq_game_player_stat"),
        ]
        indexes = [
            models.Index(fields=["game", "team"]),
            models.Index(fields=["game", "player"]),
        ]

    @property
    def rebounds_total(self) -> int:
        return int(self.rebounds_off + self.rebounds_def)

    def clean(self):
        if self.player_id and self.team_id and self.player.team_id != self.team_id:
            raise ValidationError({"player": "Игрок должен принадлежать выбранной команде."})

    @staticmethod
    def pct(made: int, att: int) -> float:
        return float(made * 100.0 / att) if att else 0.0

    @property
    def shots_pct(self) -> float:
        return self.pct(self.shots_made, self.shots_att)

    @property
    def fg2_pct(self) -> float:
        return self.pct(self.fg2_made, self.fg2_att)

    @property
    def ft_pct(self) -> float:
        return self.pct(self.ft_made, self.ft_att)


class TeamGameStat(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="team_stats", verbose_name="Матч")
    team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="team_stats", verbose_name="Команда")

    points = models.PositiveIntegerField("Очки", default=0)
    assists = models.PositiveIntegerField("Передачи", default=0)
    rebounds_off = models.PositiveIntegerField("Подборы (нап.)", default=0)
    rebounds_def = models.PositiveIntegerField("Подборы (защ.)", default=0)
    steals = models.PositiveIntegerField("Перехваты", default=0)
    turnovers = models.PositiveIntegerField("Потери", default=0)
    blocks = models.PositiveIntegerField("Блок-шоты", default=0)
    fouls = models.PositiveIntegerField("Фолы игрока", default=0)
    fouls_against = models.PositiveIntegerField("Фолы соперника", default=0)

    shots_att = models.PositiveIntegerField("Броски: попытки", default=0)
    shots_made = models.PositiveIntegerField("Броски: попадания", default=0)
    fg2_att = models.PositiveIntegerField("2 очка: попытки", default=0)
    fg2_made = models.PositiveIntegerField("2 очка: попадания", default=0)
    ft_att = models.PositiveIntegerField("Штрафные: попытки", default=0)
    ft_made = models.PositiveIntegerField("Штрафные: попадания", default=0)

    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        verbose_name = "Командная статистика (матч)"
        verbose_name_plural = "Командная статистика (матч)"
        constraints = [models.UniqueConstraint(fields=["game", "team"], name="uniq_game_team_stat")]
        indexes = [models.Index(fields=["game", "team"])]

    @property
    def rebounds_total(self) -> int:
        return int(self.rebounds_off + self.rebounds_def)

    @property
    def shots_pct(self) -> float:
        return float(self.shots_made * 100.0 / self.shots_att) if self.shots_att else 0.0

    @property
    def fg2_pct(self) -> float:
        return float(self.fg2_made * 100.0 / self.fg2_att) if self.fg2_att else 0.0

    @property
    def ft_pct(self) -> float:
        return float(self.ft_made * 100.0 / self.ft_att) if self.ft_att else 0.0

