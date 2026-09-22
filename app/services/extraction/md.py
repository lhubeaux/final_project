import re
from typing import BinaryIO

from app.services.extraction.txt import decoder

# Le Markdown n'est pas un format de fichier mais une convention d'écriture :
# le décodage est celui d'un .txt. Le nettoyage qui suit est volontairement
# minimal — il retire les marques pour qu'elles ne soient pas comptées comme
# des mots, sans prétendre interpréter le balisage ni ajouter de dépendance.
_TITRE = re.compile(r"^#{1,6}[ \t]+", re.MULTILINE)
_CITATION = re.compile(r"^[ \t]*>[ \t]?", re.MULTILINE)
_PUCE = re.compile(r"^[ \t]*(?:[-*+]|\d+\.)[ \t]+", re.MULTILINE)
_LIEN = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_EMPHASE = re.compile(r"(\*{1,3}|_{1,3})(\S.*?\S|\S)\1")
_CODE = re.compile(r"`+")


def extraire_md(flux: BinaryIO) -> str:
    texte = decoder(flux.read())

    texte = _TITRE.sub("", texte)
    texte = _CITATION.sub("", texte)
    texte = _PUCE.sub("", texte)
    texte = _LIEN.sub(r"\1", texte)      # garde le libellé, jette l'URL
    texte = _EMPHASE.sub(r"\2", texte)
    texte = _CODE.sub("", texte)

    return texte
