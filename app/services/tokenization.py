import re

def tokenize(phrase: str) -> list[dict]:
    result = []

    for match in re.finditer(r"\S+", phrase):                    #trouve chaque mot/ponctuation et sa position
        token = {"texte": match.group(), "start": match.start(), "end": match.end()}
        result.append(token)                                     #ajoute le token à la liste
    return result
