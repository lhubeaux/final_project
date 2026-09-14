from flask import Blueprint, render_template, request

from collections import Counter

from app.services.document import build_document
from app.services.rendering import surligner
from app.services.rules import regles, run

bp = Blueprint("analyze", __name__)


@bp.route("/", methods=["GET", "POST"])
def index():
    document = None
    findings = []
    texte_surligne = None
    resume = []

    if request.method == "POST":
        document = build_document(request.form["texte"])
        findings = run(document)
        texte_surligne = surligner(document.texte, findings)

        # Le résumé part des règles actives, pas des signalements : une règle qui
        # n'a rien trouvé doit apparaître avec un zéro, c'est une information.
        comptes = Counter(finding.rule_id for finding in findings)
        resume = [(regle.hint, comptes[regle.id]) for regle in regles(document.langue)]

    return render_template(
        "analyze/index.html",
        document=document,
        findings=findings,
        texte_surligne=texte_surligne,
        resume = resume
    )
