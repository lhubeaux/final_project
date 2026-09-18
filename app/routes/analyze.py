from flask import Blueprint, render_template, request

from collections import Counter

from app.services.document import build_document
from app.services.extraction import ExtractionError, extensions_supportees, extraire
from app.services.rendering import surligner
from app.services.rules import regles, run

bp = Blueprint("analyze", __name__)


@bp.route("/", methods=["GET", "POST"])
def index():
    document = None
    findings = []
    texte_surligne = None
    resume = []
    erreur = None

    if request.method == "POST":
        fichier = request.files.get("fichier")

        try:
            # Le fichier l'emporte sur la zone de texte : si l'utilisateur a
            # rempli les deux, il a fait un geste plus explicite en déposant un
            # fichier. `filename` est vide quand aucun fichier n'a été choisi.
            if fichier and fichier.filename:
                texte_brut = extraire(fichier.filename, fichier.stream)
            else:
                texte_brut = request.form.get("texte", "")
        except ExtractionError as echec:
            # Le message d'un ExtractionError est écrit pour être affiché tel
            # quel : la route ne le reformule pas.
            erreur = str(echec)
            texte_brut = ""

        if texte_brut.strip():
            document = build_document(texte_brut, langue="fr")
            findings = run(document)
            texte_surligne = surligner(document.texte, findings)

            # Le résumé part des règles actives, pas des signalements : une règle qui
            # n'a rien trouvé doit apparaître avec un zéro, c'est une information.
            comptes = Counter(finding.rule_id for finding in findings)
            resume = [(regle.hint, comptes[regle.id]) for regle in regles(document.langue)]
        elif erreur is None:
            erreur = "Aucun texte à analyser."

    return render_template(
        "analyze/index.html",
        document=document,
        findings=findings,
        texte_surligne=texte_surligne,
        resume=resume,
        erreur=erreur,
        extensions=extensions_supportees(),
    )
