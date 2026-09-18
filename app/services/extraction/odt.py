from typing import BinaryIO, Iterator

from odf import teletype
from odf.element import Element
from odf.namespaces import TEXTNS
from odf.opendocument import load

from app.services.extraction.registry import FichierIllisible, enregistrer

# Les qnames sont construits à la main : instancier `H()` exigerait son
# attribut obligatoire `outlinelevel`, inutile ici puisqu'on ne fait que
# comparer des noms de balises.
_BLOCS = {(TEXTNS, "p"), (TEXTNS, "h")}      # paragraphes et titres


def _parcourir(noeud: Element) -> Iterator[str]:
    """Descend l'arbre en profondeur pour garder l'ordre du document.

    `getElementsByType()` regrouperait tous les paragraphes puis tous les
    titres : l'ordre de lecture serait perdu.
    """
    for enfant in noeud.childNodes:
        if not isinstance(enfant, Element):
            continue
        if enfant.qname in _BLOCS:
            yield teletype.extractText(enfant)
        else:
            yield from _parcourir(enfant)


@enregistrer(".odt")
def extraire_odt(flux: BinaryIO) -> str:
    """Le texte des paragraphes et titres d'un .odt, dans l'ordre de lecture.

    Comme le .docx, un .odt est une archive ZIP contenant du XML : l'encodage
    y est déclaré, et la ligne vide entre deux blocs est ce que `segment()`
    attend pour délimiter un paragraphe.
    """
    try:
        odt = load(flux)
    except Exception as erreur:
        raise FichierIllisible("Fichier .odt illisible ou corrompu.") from erreur

    blocs = [bloc.strip() for bloc in _parcourir(odt.text)]

    return "\n\n".join(bloc for bloc in blocs if bloc)
