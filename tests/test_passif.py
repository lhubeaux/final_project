import pytest

from app.services.document import build_document
from app.services.linguistics import modele
from app.services.rules.fr import Passif


@pytest.fixture(scope="session")
def nlp():
    """Charge spaCy une fois pour toute la session de tests."""
    return modele()


def signale(texte: str):
    return Passif().check(build_document(texte))


@pytest.mark.parametrize(
    ("texte", "empan", "severity"),
    [
        (
            "La décision a été prise par le conseil.",
            "a été prise",
            "info",
        ),
        (
            "La décision a été prise.",
            "a été prise",
            "avertissement",
        ),
    ],
)
def test_passif_signale_le_groupe_verbal(texte, empan, severity, nlp):
    findings = signale(texte)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "passif"
    assert finding.severity == severity
    assert texte[finding.char_start:finding.char_end] == empan


def test_passe_compose_avec_etre_n_est_pas_un_passif(nlp):
    assert signale("Elle est allée à Paris.") == []


@pytest.mark.xfail(
    reason="« La porte est ouverte » peut décrire un état ou une action : limite assumée."
)
def test_etat_ambigu_non_signale_comme_passif(nlp):
    assert signale("La porte est ouverte.") == []