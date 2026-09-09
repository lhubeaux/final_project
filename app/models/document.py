from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import db, maintenant

if TYPE_CHECKING:
    from app.models.analysis import Analysis

class DocumentRecord(db.Model):
    """Un texte soumis.

    `texte` est le texte NORMALISÉ : c'est lui qui fait référence, et tous les
    empans des findings sont des index dans cette chaîne-là (D-4).
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    texte: Mapped[str] = mapped_column(Text)
    langue: Mapped[str] = mapped_column(default="fr")
    source: Mapped[str] = mapped_column(default="saisie")     # saisie | fichier
    nom_fichier: Mapped[str | None]
    version_tokeniseur: Mapped[int] = mapped_column(default=1)
    cree_le: Mapped[datetime] = mapped_column(default=maintenant)

    analyses: Mapped[list["Analysis"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

