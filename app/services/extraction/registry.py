"""Registre des extracteurs de texte (D-8).

Un extracteur reçoit un flux binaire et renvoie du texte BRUT. La
normalisation reste le travail de `build_document()`, seul point d'entrée du
moteur : un extracteur qui normaliserait lui-même casserait l'invariant, car
deux chemins d'entrée produiraient deux textes de référence différents.
"""

from pathlib import Path
from typing import BinaryIO, Callable


class ExtractionError(Exception):
    """Erreur d'import dont le message est montrable à l'utilisateur."""


class FormatNonSupporte(ExtractionError):
    """L'extension n'a pas d'extracteur enregistré."""


class FichierIllisible(ExtractionError):
    """Le fichier a la bonne extension mais ne s'ouvre pas."""


Extracteur = Callable[[BinaryIO], str]

_registre: dict[str, Extracteur] = {}

# Refusés volontairement (D-2) : mise en page figée pour .pdf, format binaire
# propriétaire pour .doc. Un message dédié vaut mieux qu'un « format inconnu ».
_REFUS = {
    ".pdf": "Le PDF n'est pas accepté : le texte y est disposé, pas structuré.",
    ".doc": "Le format .doc n'est pas accepté. Enregistrez le fichier en .docx.",
}


def enregistrer(*extensions: str) -> Callable[[Extracteur], Extracteur]:
    """Décorateur : range la fonction dans le registre pour ces extensions."""

    def decorateur(fonction: Extracteur) -> Extracteur:
        for extension in extensions:
            _registre[extension.lower()] = fonction
        return fonction

    return decorateur


def extensions_supportees() -> tuple[str, ...]:
    """Les extensions acceptées, pour le formulaire et les messages d'erreur."""
    return tuple(sorted(_registre))


def extraire(nom_fichier: str, flux: BinaryIO) -> str:
    """Renvoie le texte brut du fichier, d'après son extension.

    Le nom vient du client : il ne sert qu'à choisir l'extracteur, jamais à
    écrire sur le disque.
    """
    extension = Path(nom_fichier).suffix.lower()

    if extension in _REFUS:
        raise FormatNonSupporte(_REFUS[extension])

    extracteur = _registre.get(extension)
    if extracteur is None:
        raise FormatNonSupporte(
            f"Format « {extension or 'sans extension'} » non pris en charge. "
            f"Formats acceptés : {', '.join(extensions_supportees())}."
        )

    return extracteur(flux)
