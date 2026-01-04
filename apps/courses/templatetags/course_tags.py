"""
Template tags and filters for courses app.
"""

from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Get an item from a dictionary by key.
    Usage: {{ mydict|get_item:key }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def duration_format(minutes):
    """
    Format duration in minutes to human readable format.
    Usage: {{ 90|duration_format }} -> "1h 30m"
    """
    if not minutes:
        return "0m"
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0:
        if mins > 0:
            return f"{hours}h {mins}m"
        return f"{hours}h"
    return f"{mins}m"


@register.filter
def progress_color(progress):
    """
    Get color class based on progress percentage.
    """
    if progress >= 100:
        return "success"
    elif progress >= 50:
        return "primary"
    elif progress >= 25:
        return "warning"
    return "error"
