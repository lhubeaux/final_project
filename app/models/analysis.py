from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import db, maintenant

if TYPE_CHECKING:
    from app.models.document import DocumentRecord
    from app.models.finding import FindingRecord


class Analysis(db.Model):
    """Une exécution du moteur de règles sur un document."""

    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    nom: Mapped[str]                       # donné par l'utilisateur à l'enregistrement
    cree_le: Mapped[datetime] = mapped_column(default=maintenant)

    document: Mapped["DocumentRecord"] = relationship(back_populates="analyses")
    findings: Mapped[list["FindingRecord"]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="FindingRecord.id",      # ordre d'insertion = ordre de run()
    )

