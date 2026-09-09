import re


def tokenize(phrase: str, offset: int = 0) -> list[dict]:
    """offset : position de la phrase dans le texte normalisé.

    Les positions renvoyées sont absolues, jamais relatives à la phrase.
    """
    result = []

    for match in re.finditer(r"\S+", phrase):           # chaque mot / ponctuation et sa position
        token = {
            "texte": match.group(),
            "start": offset + match.start(),            # reportée sur le texte complet
            "end": offset + match.end(),
        }
        result.append(token)

    return result
