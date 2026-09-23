from dataclasses import dataclass
from functools import cache

import spacy
from spacy.language import Language


@dataclass(frozen=True)
class TokenLinguistique:
    """Projection minimale d'un token spaCy, indépendante de spaCy."""

    texte: str
    lemme: str
    categorie: str
    fonction: str
    gouverneur: int
    start: int
    end: int


@cache
def modele() -> Language:
    """Charge le modèle une seule fois, au premier besoin."""
    return spacy.load("fr_core_news_sm", exclude=["ner"])


def analyser_phrases(
    phrases: list[tuple[str, int]],
) -> list[list[TokenLinguistique]]:
    """Analyse des phrases et reporte les positions dans le texte complet.

    Chaque tuple contient le texte d'une phrase et sa position de départ
    absolue dans le document.
    """
    if not phrases:
        return []
    textes = [texte for texte, _ in phrases]
    analyses = []

    for (_, offset), doc in zip(phrases, modele().pipe(textes)):
        analyses.append([
            TokenLinguistique(
                texte=token.text,
                lemme=token.lemma_,
                categorie=token.pos_,
                fonction=token.dep_,
                gouverneur=token.head.i,
                start=offset + token.idx,
                end=offset + token.idx + len(token.text),
            )
            for token in doc
        ])

    return analyses
