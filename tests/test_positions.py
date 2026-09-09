from app.services.normalization import normalize
from app.services.segmentation import segment
from app.services.tokenization import tokenize


def test_positions_absolues():
    texte = normalize("Titre du décret\r\n\r\nL\u2019examen a été effectué par la commission.")

    for paragraphe in segment(texte):
        for phrase in paragraphe:
            assert texte[phrase["start"]:phrase["end"]] == phrase["texte"]

            for token in tokenize(phrase["texte"], phrase["start"]):
                assert texte[token["start"]:token["end"]] == token["texte"]
