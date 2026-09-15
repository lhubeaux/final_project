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


@pytest.mark.parametrize(
    "texte",
    [
        "Le demandeur est susceptible d'obtenir un délai.",
        "Aucune démarche n'est nécessaire.",
    ],
)
def test_attribut_adjectif_n_est_pas_un_passif(texte, nlp):
    assert signale(texte) == []


def test_passif_au_futur_sans_agent(nlp):
    texte = "Le rapport sera publié demain."
    findings = signale(texte)

    assert len(findings) == 1
    assert texte[findings[0].char_start:findings[0].char_end] == "sera publié"
    assert findings[0].severity == "avertissement"


def test_positions_de_l_analyse_linguistique(nlp):
    document = build_document("Titre\n\nLa décision a été prise par le conseil.")

    for phrase in document.phrases:
        for token in phrase.analyse:
            assert document.texte[token.start:token.end] == token.texte
