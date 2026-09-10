from flask import Blueprint, render_template, request

from app.services.document import build_document
from app.services.rendering import surligner
from app.services.rules import run

bp = Blueprint("analyze", __name__)


@bp.route("/", methods=["GET", "POST"])
def index():
    document = None
    findings = []
    texte_surligne = None

    if request.method == "POST":
        document = build_document(request.form["texte"])
        findings = run(document)
        texte_surligne = surligner(document.texte, findings)

    return render_template(
        "analyze/index.html",
        document=document,
        findings=findings,
        texte_surligne=texte_surligne,
    )
