from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

from app.services.document import Document


@dataclass(frozen=True)
class Finding:
    """Un signalement, tel qu'il circule entre les couches (D-5, D-6).

    `char_start` et `char_end` sont des index dans le texte normalisé du
    Document analysé. C'est vrai de TOUTE règle, quelle que soit sa granularité.
    """

    rule_id: str
    hint: str
    severity: str
    char_start: int
    char_end: int
    message: str
    suggestion: str | None = None


class Rule(ABC):
    """Contrat commun à toutes les règles (D-8).

    Une règle concrète redéfinit les quatre attributs qui l'identifient,
    puis implémente `check()`. Elle ne garde aucun état sur `self` :
    l'instance est partagée par toutes les requêtes.
    """

    id: str = ""
    hint: str = ""
    severity: Literal["info", "avertissement"] = "avertissement"
    langues: tuple[str, ...] = ()

    def s_applique_a(self, langue: str) -> bool:
        """La règle sait-elle traiter cette langue ?"""
        return langue in self.langues

    def signaler(
        self,
        char_start: int,
        char_end: int,
        message: str,
        suggestion: str | None = None,
    ) -> Finding:
        """Fabrique un Finding en y reportant l'identité de la règle."""
        return Finding(
            rule_id=self.id,
            hint=self.hint,
            severity=self.severity,
            char_start=char_start,
            char_end=char_end,
            message=message,
            suggestion=suggestion,
        )

    @abstractmethod
    def check(self, document: Document) -> list[Finding]:
        """Renvoie les signalements trouvés dans le document."""