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
    text = request.form["texte"]
    text = normalize(text)
    phrases = segment(text)

    tokens = []
    for paragraph in phrases:
        para_tokens = []
        for phrase in paragraph:
            para_tokens.append(tokenize(phrase))
        tokens.append(para_tokens)
    return render_template("analyze/index.html", texte=text, phrases = phrases,tokens = tokens)

