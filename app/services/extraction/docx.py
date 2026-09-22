from typing import BinaryIO

from docx import Document as DocumentDocx

from app.services.extraction.base import FichierIllisible


def extraire_docx(flux: BinaryIO) -> str:
    """Le texte des paragraphes d'un .docx, séparés par une ligne vide.

    Un .docx est une archive ZIP contenant du XML : l'encodage y est déclaré,
    donc aucune devinette n'est nécessaire. La ligne vide n'est pas cosmétique,
    c'est ce que `segment()` attend pour délimiter un paragraphe.

    Limite connue : `paragraphs` ignore le texte des tableaux.
    """
    try:
        docx = DocumentDocx(flux)
    except Exception as erreur:      # python-docx lève des types variés
        raise FichierIllisible("Fichier .docx illisible ou corrompu.") from erreur

    paragraphes = [paragraphe.text.strip() for paragraphe in docx.paragraphs]

    return "\n\n".join(paragraphe for paragraphe in paragraphes if paragraphe)
