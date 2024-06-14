from django import template

register = template.Library()


@register.filter(name="remove_linebreaks")
def remove_linebreaks(value):
    """Remove all newlines and carriage returns from the string."""
    return value.replace("\n", "").replace("\r", "")
