from __future__ import annotations

from django import template

register = template.Library()


@register.simple_tag
def media_or_static(media_url: str | None, static_url: str) -> str:
    return media_url or static_url

