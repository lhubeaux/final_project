from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import db

if TYPE_CHECKING:
    from app.models.analysis import Analysis


class FindingRecord(db.Model):
    """Reflet persisté de la dataclass `Finding` (D-6) : mêmes champs, nom distinct."""

    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id"))

    rule_id: Mapped[str]
    hint: Mapped[str]
    severity: Mapped[str]
    char_start: Mapped[int]
    char_end: Mapped[int]
    message: Mapped[str] = mapped_column(Text)
    suggestion: Mapped[str | None] = mapped_column(Text)

    analysis: Mapped["Analysis"] = relationship(back_populates="findings")
