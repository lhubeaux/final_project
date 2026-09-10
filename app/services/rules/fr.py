from app.services.document import Document
from app.services.rules.base import Finding, Rule
from app.services.rules.runner import enregistrer


@enregistrer
class LongueurPhrase(Rule):
    """Signale les phrases qui dépassent le seuil de mots fixé pour la langue."""

    id = "longueur_phrase"
    hint = "P4 — faire court et simple"
    severity = "avertissement"
    langues = ("fr",)

    seuils = {"fr": 25, "en": 21}          # D-11 : une phrase française est plus longue

    def check(self, document: Document) -> list[Finding]:
        seuil = self.seuils[document.langue]
        findings = []

        for phrase in document.phrases:
            mots = len(phrase.tokens)
            if mots > seuil:
                findings.append(self.signaler(
                    phrase.start,
                    phrase.end,
                    f"Phrase de {mots} mots (seuil : {seuil}). "
                    f"Envisagez de la couper en deux.",
                ))

        return findings
