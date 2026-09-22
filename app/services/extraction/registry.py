"""Registre des extracteurs : quelle extension confie son flux à quelle fonction.

La table est écrite en clair. Le jeu de formats est arrêté (D-2), donc
l'énumérer se lit mieux qu'un enregistrement automatique : tout ce que le
programme accepte tient dans les quelques lignes de `REGISTRE`.
"""

from pathlib import Path
from typing import BinaryIO

from app.services.extraction.base import Extracteur, FormatNonSupporte
from app.services.extraction.docx import extraire_docx
from app.services.extraction.md import extraire_md
from app.services.extraction.odt import extraire_odt
from app.services.extraction.txt import extraire_txt

REGISTRE: dict[str, Extracteur] = {
    ".txt": extraire_txt,
    ".md": extraire_md,
    ".docx": extraire_docx,
    ".odt": extraire_odt,
}

# Refusés volontairement (D-2) : mise en page figée pour .pdf, format binaire
# propriétaire pour .doc. Un message dédié vaut mieux qu'un « format inconnu ».
_REFUS = {
    ".pdf": "Le PDF n'est pas accepté : le texte y est disposé, pas structuré.",
    ".doc": "Le format .doc n'est pas accepté. Enregistrez le fichier en .docx.",
}


def extensions_supportees() -> tuple[str, ...]:
    """Les extensions acceptées, pour le formulaire et les messages d'erreur."""
    return tuple(sorted(REGISTRE))


def extraire(nom_fichier: str, flux: BinaryIO) -> str:
    """Renvoie le texte brut du fichier, d'après son extension.

    Le nom vient du client : il ne sert qu'à choisir l'extracteur, jamais à
    écrire sur le disque.
    """
    extension = Path(nom_fichier).suffix.lower()

    if extension in _REFUS:
        raise FormatNonSupporte(_REFUS[extension])

    extracteur = REGISTRE.get(extension)
    if extracteur is None:
        raise FormatNonSupporte(
            f"Format « {extension or 'sans extension'} » non pris en charge. "
            f"Formats acceptés : {', '.join(extensions_supportees())}."
        )

    return extracteur(flux)
