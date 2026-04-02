from __future__ import annotations

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class Season(models.Model):
    name = models.CharField("Сезон", max_length=64, unique=True)
    is_active = models.BooleanField("Активный", default=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "Сезон"
        verbose_name_plural = "Сезоны"
        ordering = ["-is_active", "-id"]

    def __str__(self) -> str:
        return self.name


class Team(models.Model):
    name = models.CharField("Название", max_length=120, unique=True)
    short_name = models.CharField("Коротко", max_length=16, blank=True, default="")
    city = models.CharField("Город", max_length=80, blank=True, default="")
    logo = models.ImageField("Логотип", upload_to="team_logos/", blank=True, null=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "Команда"
        verbose_name_plural = "Команды"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Player(models.Model):
    team = models.ForeignKey(Team, related_name="players", on_delete=models.PROTECT, verbose_name="Команда")
    first_name = models.CharField("Имя", max_length=60)
    last_name = models.CharField("Фамилия", max_length=60)
    photo = models.ImageField("Фото", upload_to="player_photos/", blank=True, null=True)
    number = models.PositiveSmallIntegerField(
        "Номер",
        validators=[MinValueValidator(0), MaxValueValidator(99)],
        blank=True,
        null=True,
    )
    position = models.CharField("Позиция", max_length=32, blank=True, default="")
    height_cm = models.PositiveSmallIntegerField("Рост (см)", blank=True, null=True)
    weight_kg = models.PositiveSmallIntegerField("Вес (кг)", blank=True, null=True)
    birth_date = models.DateField("Дата рождения", blank=True, null=True)
    is_active = models.BooleanField("Активен", default=True)
    search_name = models.CharField(max_length=200, editable=False, db_index=True, default="")

    class Meta:
        verbose_name = "Игрок"
        verbose_name_plural = "Игроки"
        ordering = ["last_name", "first_name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["team", "number"],
                condition=Q(number__isnull=False),
                name="uniq_team_number_when_present",
            )
        ]

    def __str__(self) -> str:
        n = f" #{self.number}" if self.number is not None else ""
        return f"{self.last_name} {self.first_name}{n}"

    def save(self, *args, **kwargs):
        self.search_name = f"{self.last_name} {self.first_name}".strip().lower()
        super().save(*args, **kwargs)


class Game(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Запланирован"
        LIVE = "live", "В лайве"
        FINISHED = "finished", "Завершён"

    season = models.ForeignKey(Season, on_delete=models.PROTECT, verbose_name="Сезон", related_name="games")
    home_team = models.ForeignKey(Team, on_delete=models.PROTECT, verbose_name="Хозяева", related_name="home_games")
    away_team = models.ForeignKey(Team, on_delete=models.PROTECT, verbose_name="Гости", related_name="away_games")
    start_at = models.DateTimeField("Начало", default=timezone.now)
    status = models.CharField("Статус", max_length=16, choices=Status.choices, default=Status.SCHEDULED)
    venue = models.CharField("Арена", max_length=120, blank=True, default="")
    current_period = models.PositiveSmallIntegerField("Текущий период", default=1)
    clock_seconds = models.PositiveSmallIntegerField("Секунды на табло", default=10 * 60)
    clock_running = models.BooleanField("Часы идут", default=False)
    period_duration = models.PositiveSmallIntegerField("Длительность периода (сек.)", default=10 * 60)
    clock_updated_at = models.DateTimeField("Время обновления часов", default=timezone.now)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "Матч"
        verbose_name_plural = "Матчи"
        ordering = ["-start_at", "-id"]
        constraints = [
            models.CheckConstraint(check=~models.Q(home_team=models.F("away_team")), name="home_team_not_away_team"),
        ]

    def __str__(self) -> str:
        return f"{self.home_team} — {self.away_team} ({self.start_at:%d.%m.%Y})"


class GameRoster(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, verbose_name="Матч", related_name="rosters")
    team = models.ForeignKey(Team, on_delete=models.PROTECT, verbose_name="Команда", related_name="rosters")
    player = models.ForeignKey(Player, on_delete=models.PROTECT, verbose_name="Игрок", related_name="rosters")
    is_starter = models.BooleanField("В старте", default=False)
    is_active = models.BooleanField("В заявке", default=True)

    class Meta:
        verbose_name = "Заявка на матч"
        verbose_name_plural = "Заявки на матч"
        constraints = [
            models.UniqueConstraint(fields=["game", "player"], name="uniq_game_player"),
        ]

    def __str__(self) -> str:
        return f"{self.game}: {self.player}"

    def clean(self):
        if self.player_id and self.team_id and self.player.team_id != self.team_id:
            raise ValidationError({"player": "Игрок должен принадлежать выбранной команде."})

