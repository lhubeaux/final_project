from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import db


class WordList(db.Model):
    """Une liste de mots nommée, pour une langue : « connecteurs_lourds » en français."""

    __tablename__ = "word_lists"
    __table_args__ = (UniqueConstraint("nom", "langue"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str]
    langue: Mapped[str]

    entrees: Mapped[list["WordEntry"]] = relationship(
        back_populates="liste", cascade="all, delete-orphan"
    )


class WordEntry(db.Model):
    """Une entrée de liste.

    `remplacement` reste vide pour une liste sans reformulation, comme celle des
    verbes conjugués avec être : une seule table sert les deux formes de liste.
    """

    __tablename__ = "word_entries"
    __table_args__ = (UniqueConstraint("word_list_id", "expression"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    word_list_id: Mapped[int] = mapped_column(ForeignKey("word_lists.id"))
    expression: Mapped[str]
    remplacement: Mapped[str | None]

    liste: Mapped["WordList"] = relationship(back_populates="entrees")
