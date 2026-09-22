"""Contrat des extracteurs de texte (D-8).

Un extracteur reçoit un flux binaire et renvoie du texte BRUT. La
normalisation reste le travail de `build_document()`, seul point d'entrée du
moteur : un extracteur qui normaliserait lui-même casserait l'invariant, car
deux chemins d'entrée produiraient deux textes de référence différents.

Ce module ne contient que le type et les erreurs, et n'importe rien du
projet : c'est ce qui permet à `registry.py` d'importer les extracteurs, et
aux extracteurs d'importer leurs erreurs, sans cycle d'import.
"""

from typing import BinaryIO, Callable


class ExtractionError(Exception):
    """Erreur d'import dont le message est montrable à l'utilisateur."""


class FormatNonSupporte(ExtractionError):
    """L'extension n'a pas d'extracteur dans le registre."""


class FichierIllisible(ExtractionError):
    """Le fichier a la bonne extension mais ne s'ouvre pas."""


Extracteur = Callable[[BinaryIO], str]
