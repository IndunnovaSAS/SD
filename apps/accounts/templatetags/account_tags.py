from django import template

register = template.Library()


@register.simple_tag
def default_password(user):
    """Return the parameterized default password for a user."""
    name_part = user.first_name.strip().lower()[:3] if user.first_name else "usr"
    name_part = name_part.ljust(3, "x")
    return f"{user.document_number}{name_part}"
