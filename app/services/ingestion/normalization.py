import unicodedata


def normalize(texte: str) -> str:
    texte = texte.lstrip("\ufeff")                              # enlève le BOM, en tête seulement
    texte = texte.replace("\r\n", "\n").replace("\r", "\n")     # fins de ligne Windows et Mac -> Unix
    texte = unicodedata.normalize("NFC", texte)                 # fusionne voyelle + accent combinant
    texte = texte.replace("\u00AD", "")                         # supprime le trait d'union conditionnel
    texte = texte.replace("\u2019", "'")                        # apostrophes courbes -> apostrophes droites
    texte = texte.replace("\u00A0", " ").replace("\u202F", " ") # espaces insécables -> espaces normales
    return texte
