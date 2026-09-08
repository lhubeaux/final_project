import unicodedata

def normalize(texte: str) -> str:
    texte = texte.strip("\ufeff")                               #enlève le caractère invisible du BOM
    texte = unicodedata.normalize("NFC", texte)                 #fusionne voyelle + accent
    texte = texte.replace("\u2019", "'")                        #remplacer les apostrophes courbes par des apostrophes droites
    texte = texte.replace("\u00A0", " ").replace("\u202F", " ") #remplacer les espaces insécables par des espaces normales
    return texte