import re

from app.services.document import Document
from app.services.rules.base import Finding, Rule
from app.services.rules.seuils import seuil
from app.services.rules.lexiques import (
    connecteurs_lourds,
    verbes_conjugues_avec_etre,
)


class LongueurPhrase(Rule):
    """Signale les phrases qui dépassent le seuil de mots fixé pour la langue."""

    id = "longueur_phrase"
    hint = "P4 — faire court et simple"
    severity = "avertissement"

    def s_applique_a(self, langue: str) -> bool:
        """Applicable partout où un seuil est défini — pas de liste à maintenir."""
        return seuil(self.id, langue) is not None

    def check(self, document: Document) -> list[Finding]:
        maximum = seuil(self.id, document.langue)
        findings = []

        for phrase in document.phrases:
            mots = len(phrase.tokens)
            if mots > maximum:
                findings.append(self.signaler(
                    phrase.start,
                    phrase.end,
                    f"Phrase de {mots} mots (seuil : {maximum}). "
                    f"Envisagez de la couper en deux.",
                ))

        return findings

def _motif(expression: str) -> re.Pattern[str]:
    """Transforme une expression du lexique en expression régulière.
    « afin de » doit attraper « Afin de », « afin  de » et « afin d'appliquer »."""
    mots = expression.split()                   # "afin de" -> ["afin", "de"]
    mots = [re.escape(mot) for mot in mots]     # rend littéraux ' . etc.

    if mots[-1] == "de":
        mots[-1] = r"d(?:e\b|')"                # « de » ou sa forme élidée « d' »
    else:
        mots[-1] = mots[-1] + r"\b"             # sinon, fin de mot obligatoire

    motif = r"\b" + r"\s+".join(mots)
    return re.compile(motif, re.IGNORECASE)


class ConnecteursLourds(Rule):
    """Signale les locutions administratives qui ont un équivalent plus simple."""

    id = "connecteurs_lourds"
    hint = "P5 — choisir des mots simples"
    severity = "info"

    def s_applique_a(self, langue: str) -> bool:
        """Applicable partout où un lexique existe — pas de liste à maintenir."""
        return bool(connecteurs_lourds(langue))

    def check(self, document: Document) -> list[Finding]:
        lexique = connecteurs_lourds(document.langue)
        findings = []
        occupes: set[int] = set()     # caractères déjà pris par une expression plus longue

        # Les expressions longues d'abord : « dans le cadre de » doit l'emporter
        # sur une expression plus courte qu'il contiendrait.
        for expression in sorted(lexique, key=len, reverse=True):
            for match in _motif(expression).finditer(document.texte):
                empan = range(match.start(), match.end())
                if occupes.intersection(empan):
                    continue
                occupes.update(empan)
                findings.append(self.signaler(
                    match.start(),          # positions absolues par construction :
                    match.end(),            # on balaie document.texte lui-même
                    f"« {match.group()} » alourdit la phrase.",
                    suggestion=lexique[expression],
                ))

        return findings



class Passif(Rule):
    """Signale les tournures passives et leur éventuel agent absent."""

    id = "passif"
    hint = "P8 — préciser qui fait quoi"
    severity = "info"
    langues = ("fr",)

    def check(self, document: Document) -> list[Finding]:
        findings = []
        # Une seule lecture par analyse, et non une par auxiliaire rencontré :
        # la liste vient de la base.
        verbes_etre = verbes_conjugues_avec_etre(document.langue)

        for phrase in document.phrases:
            for auxiliaire in phrase.analyse:
                if auxiliaire.fonction not in {"aux:pass", "cop"}:
                    continue

                if not 0 <= auxiliaire.gouverneur < len(phrase.analyse):
                    continue

                participe = phrase.analyse[auxiliaire.gouverneur]

                # « est susceptible », « est médecin » : attribut, pas participe
                if participe.categorie != "VERB":
                    continue

                if participe.lemme in verbes_etre:

                    continue


                auxiliaires = [
                    token
                    for token in phrase.analyse
                    if token.gouverneur == auxiliaire.gouverneur
                    and token.categorie == "AUX"
                ]
                debut = min(token.start for token in auxiliaires)

                a_un_agent = any(
                    token.gouverneur == auxiliaire.gouverneur
                    and token.fonction == "obl:agent"
                    for token in phrase.analyse
                )

                if a_un_agent:
                    message = "Tournure passive : précisez clairement qui agit."
                    severity = "info"
                else:
                    message = (
                        "Tournure passive sans agent : le lecteur ne sait pas qui agit."
                    )
                    severity = "avertissement"

                findings.append(self.signaler(
                    debut,
                    participe.end,
                    message,
                    severity=severity,
                ))

        return findings