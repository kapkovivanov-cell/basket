from django import template

register = template.Library()


@register.filter
def seconds_to_mmss(value):
    try:
        total = int(value)
    except (TypeError, ValueError):
        return "00:00"
    if total < 0:
        total = 0
    m, s = divmod(total, 60)
    return f"{m:02d}:{s:02d}"

