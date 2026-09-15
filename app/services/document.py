from dataclasses import dataclass, field
from typing import Any

from app.services.normalization import normalize
from app.services.segmentation import segment
from app.services.tokenization import tokenize
from app.services.linguistics import TokenLinguistique, analyser_phrases


@dataclass(frozen=True) #frozen=True empêche de réassigner un span après le traitement
class Token:
    texte: str
    start: int
    end: int


@dataclass(frozen=True)
class Sentence:
    texte: str
    start: int
    end: int
    tokens: list[Token]
    analyse: list[TokenLinguistique]


@dataclass(frozen=True)
class Paragraph:
    texte: str
    start: int
    end: int
    phrases: list[Sentence]


@dataclass(frozen=True)
class Document:
    """Ce que reçoit `check()` (D-3).

    `texte` est le texte normalisé : c'est LE texte de référence, et toutes les
    positions portées par les paragraphes, phrases et tokens sont des index
    dans cette chaîne-là.
    """

    texte: str
    langue: str
    paragraphes: list[Paragraph]
    spacy_doc: Any | None = field(default=None, compare=False)   # rempli en phase 2

    @property
    def phrases(self) -> list[Sentence]:
        """Toutes les phrases du document, frontières de paragraphe aplaties."""
        return [ph for para in self.paragraphes for ph in para.phrases]

    @property
    def tokens(self) -> list[Token]:
        """Tous les tokens du document."""
        return [tok for ph in self.phrases for tok in ph.tokens]


def build_document(texte_brut: str, langue: str = "fr") -> Document:
    """Seul point d'entrée : normalise, segmente, tokenise, assemble.

    La normalisation est faite ICI et nulle part ailleurs (D-4) : impossible de
    construire un Document dont le texte ne serait pas le texte de référence.
    """
    texte = normalize(texte_brut)

    paragraphes_source = segment(texte)
    phrases_source = [
        (phrase["texte"], phrase["start"])
        for para in paragraphes_source
        for phrase in para["phrases"]
    ]
    analyses = iter(analyser_phrases(phrases_source))

    paragraphes = []
    for para in paragraphes_source:
        phrases = []
        for phrase in para["phrases"]:
            tokens = [
                Token(texte=t["texte"], start=t["start"], end=t["end"])
                for t in tokenize(phrase["texte"], phrase["start"])
            ]
            phrases.append(Sentence(
                texte=phrase["texte"],
                start=phrase["start"],
                end=phrase["end"],
                tokens=tokens,
                analyse=next(analyses),
            ))
        paragraphes.append(Paragraph(
            texte=para["texte"],
            start=para["start"],
            end=para["end"],
            phrases=phrases,
        ))

    return Document(texte=texte, langue=langue, paragraphes=paragraphes)
