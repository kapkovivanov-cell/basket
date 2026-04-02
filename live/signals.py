from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import GameEvent
from .services import recompute_game_stats


@receiver(post_save, sender=GameEvent)
def _recompute_on_save(sender, instance: GameEvent, **kwargs):
    recompute_game_stats(instance.game_id)


@receiver(post_delete, sender=GameEvent)
def _recompute_on_delete(sender, instance: GameEvent, **kwargs):
    recompute_game_stats(instance.game_id)

