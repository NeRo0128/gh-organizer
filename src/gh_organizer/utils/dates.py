# src/gh_organizer/utils/dates.py
from datetime import UTC, datetime


def format_date(iso: str) -> str:
    """Convierte un ISO timestamp a algo como 'hace 3 días'."""
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso)
        now = datetime.now(UTC)
        delta = now - dt
        if delta.days == 0:
            hours = delta.seconds // 3600
            if hours == 0:
                return "hace unos minutos"
            return f"hace {hours}h"
        if delta.days == 1:
            return "ayer"
        if delta.days < 30:
            return f"hace {delta.days} días"
        if delta.days < 365:
            months = delta.days // 30
            return f"hace {months} mes{'es' if months > 1 else ''}"
        years = delta.days // 365
        return f"hace {years} año{'s' if years > 1 else ''}"
    except ValueError:
        return iso
