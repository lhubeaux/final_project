from typing import BinaryIO

from charset_normalizer import from_bytes

from app.services.extraction.registry import FichierIllisible, enregistrer

# Sur un texte court, l'heuristique de charset-normalizer peut élire un
# encodage asiatique et rendre des idéogrammes. On restreint donc les
# candidats aux encodages réellement rencontrés dans l'Union : latin
# occidental et central, cyrillique, grec. La liste est ouverte — elle ne
# suppose ni le français ni l'anglais.
_CANDIDATS = [
    "utf_8",
    "utf_16",
    "cp1252",       # Windows, Europe occidentale
    "iso8859_15",   # latin-9, avec le signe €
    "cp1250",       # Europe centrale
    "cp1251",       # cyrillique
    "cp1253",       # grec
]


def decoder(donnees: bytes) -> str:
    """Décode des octets sans connaître leur encodage.

    L'encodage n'est écrit nulle part dans un fichier texte : il faut le
    deviner. On essaie d'abord l'UTF-8, largement dominant et auto-vérifiant —
    des octets qui ne sont pas de l'UTF-8 échouent presque toujours au lieu de
    produire un faux texte. Sinon on laisse charset-normalizer trancher.

    On refuse plutôt que de rendre des « Ã© » : sur du mojibake, la
    segmentation et l'étiquetage seraient faux sans lever la moindre erreur,
    et les signalements porteraient sur des mots qui n'existent pas.
    """
    if not donnees:
        return ""

    try:
        return donnees.decode("utf_8_sig")      # retire le BOM s'il y en a un
    except UnicodeDecodeError:
        pass

    meilleure = from_bytes(donnees, cp_isolation=_CANDIDATS).best()
    if meilleure is None:
        raise FichierIllisible("Encodage du fichier non reconnu.")

    return str(meilleure)


@enregistrer(".txt")
def extraire_txt(flux: BinaryIO) -> str:
    return decoder(flux.read())
