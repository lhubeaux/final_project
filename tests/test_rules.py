"""Tests du moteur de règles, sans base de données.

Aucune fixture, aucun `client` : les règles ne connaissent que le Document.
C'est ce qui permet de lancer ce fichier seul devant le jury.
"""

from app.services.document import build_document
from app.services.rules import regles, run
from app.services.rules.fr import ConnecteursLourds, LongueurPhrase

PHRASE_LONGUE = (
    "Le présent document décrit la procédure applicable aux demandes déposées "
    "par les usagers auprès des services compétents avant la fin du mois de "
    "septembre de chaque année civile."
)


def signale(regle, texte, langue="fr"):
    """Raccourci : construit le document et exécute une seule règle dessus."""
    return regle.check(build_document(texte, langue=langue))


# --- longueur_phrase ---------------------------------------------------------

def test_phrase_courte_ne_signale_rien():
    assert signale(LongueurPhrase(), "Le texte est court.") == []


def test_phrase_longue_signale_la_phrase_entiere():
    findings = signale(LongueurPhrase(), PHRASE_LONGUE)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "longueur_phrase"
    assert PHRASE_LONGUE[finding.char_start:finding.char_end] == PHRASE_LONGUE
    assert "28 mots" in finding.message


# --- connecteurs_lourds ------------------------------------------------------

def test_connecteur_signale_avec_sa_proposition():
    findings = signale(ConnecteursLourds(), "Le dossier est transmis au moyen de la plateforme.")

    assert len(findings) == 1
    assert findings[0].rule_id == "connecteurs_lourds"
    assert findings[0].suggestion == "avec"


def test_connecteur_elide_majuscule_et_double_espace():
    """Les trois tolérances du motif, vérifiées sur l'empan rendu."""
    texte = "Afin d'assurer le suivi, une notice paraît. S'agissant  de la procédure, elle est close."
    # check() rend les signalements dans l'ordre du lexique ; c'est run() qui trie.
    findings = sorted(signale(ConnecteursLourds(), texte), key=lambda f: f.char_start)

    trouves = [texte[f.char_start:f.char_end] for f in findings]
    assert trouves == ["Afin d'", "S'agissant  de"]


def test_pas_de_faux_positif_au_milieu_d_un_mot():
    """« concerne » ne doit pas être attrapé à l'intérieur de « concernent »."""
    assert signale(ConnecteursLourds(), "En ce qui concernent les parties.") == []


def test_empan_toujours_fidele_au_texte():
    """L'invariant du projet, appliqué aux signalements (D-5)."""
    texte = "Nonobstant les délais, il convient de statuer préalablement à la séance."
    document = build_document(texte)

    findings = ConnecteursLourds().check(document)
    assert len(findings) == 3

    for finding in findings:
        extrait = document.texte[finding.char_start:finding.char_end]
        # le message cite exactement ce que le surlignage va entourer
        assert f"« {extrait} »" in finding.message


# --- registre et langues -----------------------------------------------------

def test_les_trois_regles_sont_enregistrees():
    assert [regle.id for regle in regles("fr")] == [
        "longueur_phrase",
        "connecteurs_lourds",
        "passif",
    ]


def test_langue_non_couverte_ne_fait_rien_planter():
    """Le garde-fou : aucune règle ne doit tourner sans sa donnée de langue."""
    assert regles("pl") == []
    assert run(build_document(PHRASE_LONGUE, langue="pl")) == []


def test_findings_tries_par_position():
    findings = run(build_document("Afin d'agir, " + PHRASE_LONGUE))
    positions = [finding.char_start for finding in findings]
    assert positions == sorted(positions)
