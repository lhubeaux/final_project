import re

import pysbd

# instancié une seule fois : réutilisable, vérifié — deux appels donnent le même résultat
_segmenter = pysbd.Segmenter(language="fr", clean=False, char_span=True)


def segment(texte: str) -> list[list[dict]]:
    """Découpe le texte normalisé en paragraphes, puis chaque paragraphe en phrases.

    Chaque phrase porte sa position dans le texte reçu en argument, et non
    dans son paragraphe : l'invariant texte[start:end] == phrase["texte"] tient.
    """
    paragraphes = []

    # un paragraphe = des lignes consécutives sans ligne vide entre elles
    for bloc in re.finditer(r"[^\n]+(?:\n[^\n]+)*", texte):
        if not bloc.group().strip():                    # ignore un bloc fait de blancs seuls
            continue

        phrases = []
        for span in _segmenter.segment(bloc.group()):   # positions relatives au paragraphe
            phrases.append({
                "texte": span.sent,                     # la phrase complète
                "start": bloc.start() + span.start,     # reportées sur le texte complet
                                                        # bloc.start() = position du paragraphe dans le texte
                                                        # span.start = position de la phrase dans le paragraphe
                "end": bloc.start() + span.end,         # idem pour la fin de phrase
            })

        paragraphes.append({
            "texte": bloc.group(),
            "start": bloc.start(),
            "end": bloc.end(),
            "phrases": phrases,
        })

    return paragraphes
