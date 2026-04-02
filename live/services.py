from __future__ import annotations

from collections import defaultdict

from django.db import transaction

from league.models import Game
from .models import GameEvent, PlayerGameStat, TeamGameStat


@transaction.atomic
def recompute_game_stats(game_id: int) -> None:
    game = Game.objects.select_related("home_team", "away_team").get(pk=game_id)
    events = (
        GameEvent.objects.filter(game_id=game_id)
        .select_related("team", "player", "related_player")
        .order_by("period", "-clock_seconds", "sequence", "id")
    )

    pstat = defaultdict(lambda: defaultdict(int))
    tstat = defaultdict(lambda: defaultdict(int))

    def add_player(team_id: int, player_id: int | None, key: str, inc: int = 1):
        if not player_id:
            return
        pstat[(team_id, player_id)][key] += inc

    def add_team(team_id: int, key: str, inc: int = 1):
        tstat[team_id][key] += inc

    for e in events:
        team_id = e.team_id
        player_id = e.player_id

        if e.event_type == GameEvent.EventType.FG2_MADE:
            add_player(team_id, player_id, "points", 2)
            add_player(team_id, player_id, "shots_att", 1)
            add_player(team_id, player_id, "shots_made", 1)
            add_player(team_id, player_id, "fg2_att", 1)
            add_player(team_id, player_id, "fg2_made", 1)
            add_team(team_id, "points", 2)
            add_team(team_id, "shots_att", 1)
            add_team(team_id, "shots_made", 1)
            add_team(team_id, "fg2_att", 1)
            add_team(team_id, "fg2_made", 1)
            if e.related_player_id:
                add_player(team_id, e.related_player_id, "assists", 1)
                add_team(team_id, "assists", 1)

        elif e.event_type == GameEvent.EventType.FG2_MISS:
            add_player(team_id, player_id, "shots_att", 1)
            add_player(team_id, player_id, "fg2_att", 1)
            add_team(team_id, "shots_att", 1)
            add_team(team_id, "fg2_att", 1)

        elif e.event_type == GameEvent.EventType.FT_MADE:
            add_player(team_id, player_id, "points", 1)
            add_player(team_id, player_id, "shots_att", 1)
            add_player(team_id, player_id, "shots_made", 1)
            add_player(team_id, player_id, "ft_att", 1)
            add_player(team_id, player_id, "ft_made", 1)
            add_team(team_id, "points", 1)
            add_team(team_id, "shots_att", 1)
            add_team(team_id, "shots_made", 1)
            add_team(team_id, "ft_att", 1)
            add_team(team_id, "ft_made", 1)

        elif e.event_type == GameEvent.EventType.FT_MISS:
            add_player(team_id, player_id, "shots_att", 1)
            add_player(team_id, player_id, "ft_att", 1)
            add_team(team_id, "shots_att", 1)
            add_team(team_id, "ft_att", 1)

        elif e.event_type == GameEvent.EventType.ASSIST:
            add_player(team_id, player_id, "assists", 1)
            add_team(team_id, "assists", 1)

        elif e.event_type == GameEvent.EventType.REB_O:
            add_player(team_id, player_id, "rebounds_off", 1)
            add_team(team_id, "rebounds_off", 1)

        elif e.event_type == GameEvent.EventType.REB_D:
            add_player(team_id, player_id, "rebounds_def", 1)
            add_team(team_id, "rebounds_def", 1)

        elif e.event_type == GameEvent.EventType.STEAL:
            add_player(team_id, player_id, "steals", 1)
            add_team(team_id, "steals", 1)

        elif e.event_type == GameEvent.EventType.TURNOVER:
            add_player(team_id, player_id, "turnovers", 1)
            add_team(team_id, "turnovers", 1)
            if e.related_player_id:
                add_player(team_id, e.related_player_id, "steals", 1)
                add_team(team_id, "steals", 1)

        elif e.event_type == GameEvent.EventType.BLOCK:
            add_player(team_id, player_id, "blocks", 1)
            add_team(team_id, "blocks", 1)

        elif e.event_type == GameEvent.EventType.FOUL:
            add_player(team_id, player_id, "fouls", 1)
            add_team(team_id, "fouls", 1)

        elif e.event_type == GameEvent.EventType.FOUL_DRAWN:
            add_player(team_id, player_id, "fouls_against", 1)
            add_team(team_id, "fouls_against", 1)

    home_id = game.home_team_id
    away_id = game.away_team_id

    TeamGameStat.objects.filter(game_id=game_id).delete()
    for tid in [home_id, away_id]:
        TeamGameStat.objects.update_or_create(
            game_id=game_id,
            team_id=tid,
            defaults=_team_defaults(tstat.get(tid, {})),
        )

    PlayerGameStat.objects.filter(game_id=game_id).delete()
    for (tid, pid), d in pstat.items():
        PlayerGameStat.objects.update_or_create(
            game_id=game_id,
            player_id=pid,
            defaults={**_player_defaults(d), "team_id": tid},
        )


def _player_defaults(d: dict[str, int]) -> dict:
    keys = [
        "points",
        "assists",
        "rebounds_off",
        "rebounds_def",
        "steals",
        "turnovers",
        "blocks",
        "fouls",
        "fouls_against",
        "shots_att",
        "shots_made",
        "fg2_att",
        "fg2_made",
        "ft_att",
        "ft_made",
    ]
    return {k: int(d.get(k, 0)) for k in keys}


def _team_defaults(d: dict[str, int]) -> dict:
    keys = [
        "points",
        "assists",
        "rebounds_off",
        "rebounds_def",
        "steals",
        "turnovers",
        "blocks",
        "fouls",
        "fouls_against",
        "shots_att",
        "shots_made",
        "fg2_att",
        "fg2_made",
        "ft_att",
        "ft_made",
    ]
    return {k: int(d.get(k, 0)) for k in keys}

