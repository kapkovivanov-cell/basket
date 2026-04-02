from __future__ import annotations

import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from league.models import Game, GameRoster, Player, Season, Team
from live.models import GameEvent
from live.services import recompute_game_stats


class Command(BaseCommand):
    help = "Очистить данные лиги и заполнить правдоподобным демо-контентом (включая 2 матча в лайве)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--admin-user",
            default="admin",
            help="Логин суперпользователя (по умолчанию: admin)",
        )
        parser.add_argument(
            "--admin-email",
            default="admin@example.com",
            help="Email суперпользователя (по умолчанию: admin@example.com)",
        )
        parser.add_argument(
            "--admin-password",
            default="admin123",
            help="Пароль суперпользователя (по умолчанию: admin123)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Очистка данных лиги и лайв-статистики..."))

        # Очистка только доменных моделей, без трогания auth/сессий.
        GameEvent.objects.all().delete()
        GameRoster.objects.all().delete()
        Game.objects.all().delete()
        Player.objects.all().delete()
        Team.objects.all().delete()
        Season.objects.all().delete()

        self.stdout.write(self.style.SUCCESS("Данные лиги очищены. Создание демо-контента..."))

        now = timezone.now()
        current_year = now.year
        season = Season.objects.create(name=f"Сезон {current_year}-{current_year + 1}", is_active=True)

        teams = self._create_teams()
        players_by_team = self._create_players(teams)

        games = self._create_games(season, teams, now)
        for g in games:
            self._create_rosters(g, players_by_team)

        # Два матча в лайве, один завершённый
        live_games = [games[0], games[1]]
        finished_game = games[2] if len(games) > 2 else games[0]

        for g in live_games:
            self._simulate_game_events(g, players_by_team, status=Game.Status.LIVE, intensity=0.6)
        self._simulate_game_events(finished_game, players_by_team, status=Game.Status.FINISHED, intensity=1.0)

        for g in games:
            recompute_game_stats(g.id)

        self._ensure_admin(
            username=options["admin_user"],
            email=options["admin_email"],
            password=options["admin_password"],
        )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Готово. Созданы:"))
        self.stdout.write(f"  Сезон: {season.name}")
        self.stdout.write(f"  Команды: {Team.objects.count()}")
        self.stdout.write(f"  Игроки: {Player.objects.count()}")
        self.stdout.write(f"  Матчи: {Game.objects.count()} (из них 2 в статусе 'Лайв')")
        self.stdout.write(f"  События: {GameEvent.objects.count()}")

    def _create_teams(self) -> list[Team]:
        data = [
            ("Северные Волки", "WOL", "Москва"),
            ("Южные Орлы", "EGL", "Сочи"),
            ("Восточные Молнии", "LTN", "Казань"),
            ("Западные Ястребы", "HWB", "Санкт-Петербург"),
        ]
        teams: list[Team] = []
        for name, short, city in data:
            teams.append(
                Team.objects.create(
                    name=name,
                    short_name=short,
                    city=city,
                )
            )
        return teams

    def _create_players(self, teams: list[Team]) -> dict[int, list[Player]]:
        first_names = ["Иван", "Алексей", "Дмитрий", "Никита", "Сергей", "Егор", "Максим", "Андрей", "Павел", "Кирилл"]
        last_names = [
            "Петров",
            "Иванов",
            "Сидоров",
            "Смирнов",
            "Кузнецов",
            "Воронов",
            "Соколов",
            "Федоров",
            "Михайлов",
            "Громов",
        ]
        positions = ["PG", "SG", "SF", "PF", "C"]

        result: dict[int, list[Player]] = {}
        for team in teams:
            players: list[Player] = []
            used_numbers: set[int] = set()
            for i in range(10):
                fn = random.choice(first_names)
                ln = random.choice(last_names)
                pos = positions[i % len(positions)]
                number = self._generate_unique_number(used_numbers)
                height = random.randint(180, 210)
                weight = random.randint(80, 115)
                p = Player.objects.create(
                    team=team,
                    first_name=fn,
                    last_name=ln,
                    number=number,
                    position=pos,
                    height_cm=height,
                    weight_kg=weight,
                    is_active=True,
                )
                players.append(p)
            result[team.id] = players
        return result

    @staticmethod
    def _generate_unique_number(used: set[int]) -> int:
        while True:
            n = random.randint(0, 99)
            if n not in used:
                used.add(n)
                return n

    def _create_games(self, season: Season, teams: list[Team], now) -> list[Game]:
        games: list[Game] = []

        pairs = [
            (teams[0], teams[1]),
            (teams[2], teams[3]),
            (teams[0], teams[2]),
        ]
        offsets = [timedelta(minutes=-15), timedelta(minutes=-5), timedelta(days=-1)]

        for (home, away), offset in zip(pairs, offsets, strict=False):
            start = now + offset
            status = Game.Status.LIVE if offset >= timedelta(days=-0.5) else Game.Status.FINISHED
            g = Game.objects.create(
                season=season,
                home_team=home,
                away_team=away,
                start_at=start,
                status=status,
                venue=f"Арена {home.city or 'Город'}",
                current_period=2 if status == Game.Status.LIVE else 4,
                clock_seconds=8 * 60 if status == Game.Status.LIVE else 0,
                clock_running=status == Game.Status.LIVE,
                period_duration=10 * 60,
                clock_updated_at=now,
            )
            games.append(g)
        return games

    def _create_rosters(self, game: Game, players_by_team: dict[int, list[Player]]) -> None:
        for team in (game.home_team, game.away_team):
            players = players_by_team[team.id]
            for idx, p in enumerate(players):
                GameRoster.objects.create(
                    game=game,
                    team=team,
                    player=p,
                    is_starter=idx < 5,
                    is_active=True,
                )

    def _simulate_game_events(
        self,
        game: Game,
        players_by_team: dict[int, list[Player]],
        status: str,
        intensity: float = 1.0,
    ) -> None:
        game.status = status
        game.save(update_fields=["status"])

        total_events = int(120 * intensity)
        sequence = 0

        for _ in range(total_events):
            team = random.choice([game.home_team, game.away_team])
            players = players_by_team[team.id]
            player = random.choice(players)

            period = random.randint(1, 4)
            clock_seconds = random.randint(0, game.period_duration)

            event_type = self._weighted_event_type()
            related_player = None

            if event_type == GameEvent.EventType.FG2_MADE and random.random() < 0.55:
                related_player = random.choice(players)
                if related_player == player:
                    related_player = None
            if event_type == GameEvent.EventType.ASSIST:
                related_player = random.choice(players)
                if related_player == player:
                    related_player = None

            sequence += 1

            GameEvent.objects.create(
                game=game,
                team=team,
                player=player,
                related_player=related_player,
                event_type=event_type,
                period=period,
                clock_seconds=clock_seconds,
                sequence=sequence,
            )

    @staticmethod
    def _weighted_event_type() -> str:
        # Распределение, имитирующее реальный матч.
        choices: list[tuple[str, float]] = [
            (GameEvent.EventType.FG2_MADE, 0.20),
            (GameEvent.EventType.FG2_MISS, 0.22),
            (GameEvent.EventType.FT_MADE, 0.08),
            (GameEvent.EventType.FT_MISS, 0.05),
            (GameEvent.EventType.ASSIST, 0.07),
            (GameEvent.EventType.REB_O, 0.08),
            (GameEvent.EventType.REB_D, 0.10),
            (GameEvent.EventType.STEAL, 0.05),
            (GameEvent.EventType.TURNOVER, 0.07),
            (GameEvent.EventType.BLOCK, 0.03),
            (GameEvent.EventType.FOUL, 0.03),
            (GameEvent.EventType.FOUL_DRAWN, 0.02),
        ]
        r = random.random()
        acc = 0.0
        for value, weight in choices:
            acc += weight
            if r <= acc:
                return value
        return choices[-1][0]

    def _ensure_admin(self, username: str, email: str, password: str) -> None:
        User = get_user_model()
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f"Суперпользователь {username!r} уже существует, пропускаю создание."))
            return
        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Создан суперпользователь {username!r} с паролем {password!r}."))

