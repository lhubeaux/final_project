from app.services.document import Document
from app.services.rules.base import Finding, Rule

_registre: list[Rule] = []


def enregistrer(classe: type[Rule]) -> type[Rule]:
    """Décorateur : instancie la règle et la range dans le registre (D-8).

    Ajouter une règle se réduit donc à une classe et une ligne — aucun code
    appelant ne change.
    """
    _registre.append(classe())
    return classe


def regles(langue: str | None = None) -> list[Rule]:
    """Les règles enregistrées, filtrées par langue si elle est précisée."""
    if langue is None:
        return list(_registre)
    return [regle for regle in _registre if regle.s_applique_a(langue)]


def run(document: Document, desactivees: frozenset[str] = frozenset()) -> list[Finding]:
    """Exécute sur le document toutes les règles applicables.

    Le résultat est trié par position : le surlignage parcourt le texte de
    gauche à droite et exige des signalements ordonnés.
    """
    findings: list[Finding] = []

    for regle in _registre:
        if not regle.s_applique_a(document.langue):
            continue
        if regle.id in desactivees:
            continue
        findings.extend(regle.check(document))

    return sorted(findings, key=lambda f: (f.char_start, f.char_end))
