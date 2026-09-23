from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


def maintenant() -> datetime:
    """Horodatage en UTC. Passée en `default=`, la fonction est appelée à
    chaque insertion — `datetime.now(timezone.utc)` serait figée à l'import."""
    return datetime.now(timezone.utc)
