"""Registre des règles et exécution sur un document (D-8, D-11).

La liste est écrite en clair, dans l'ordre d'affichage du résumé. Ajouter une
règle, c'est une classe dans le module de sa langue et une ligne ici : tout ce
que le moteur exécute se lit d'un seul coup d'œil, sans avoir à ouvrir chaque
module pour y chercher un décorateur.
"""

from app.services.ingestion.document import Document
from app.services.rules.base import Finding, Rule
from app.services.rules.fr import ConnecteursLourds, LongueurPhrase, Passif

# Des instances, pas des classes : une règle ne garde aucun état sur `self`
# (voir `Rule`), elle est donc partagée par toutes les requêtes.
REGLES: list[Rule] = [
    LongueurPhrase(),
    ConnecteursLourds(),
    Passif(),
]


def regles(langue: str | None = None) -> list[Rule]:
    """Les règles du registre, filtrées par langue si elle est précisée."""
    if langue is None:
        return list(REGLES)
    return [regle for regle in REGLES if regle.s_applique_a(langue)]


def run(document: Document, desactivees: frozenset[str] = frozenset()) -> list[Finding]:
    """Exécute sur le document toutes les règles applicables.

    Le résultat est trié par position : le surlignage parcourt le texte de
    gauche à droite et exige des signalements ordonnés.
    """
    findings: list[Finding] = []

    for regle in regles(document.langue):
        if regle.id not in desactivees:
            findings.extend(regle.check(document))

    return sorted(findings, key=lambda f: (f.char_start, f.char_end))
