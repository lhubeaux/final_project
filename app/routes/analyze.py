from flask import Blueprint, render_template, request
from app.services.normalization import normalize
from app.services.segmentation import segment
from app.services.tokenization import tokenize

bp = Blueprint("analyze", __name__)

@bp.get("/")
def index():
    return render_template("analyze/index.html")

@bp.post("/analyze")
def analyze():
    texte = normalize(request.form["texte"])
    paragraphes = segment(texte)

    for paragraphe in paragraphes:
        for phrase in paragraphe:
            phrase["tokens"] = tokenize(phrase["texte"], phrase["start"])

    return render_template("analyze/index.html", texte=texte, paragraphes=paragraphes)