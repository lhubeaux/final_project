from flask import Blueprint, render_template, request
from app.services.normalization import normalize

bp = Blueprint("analyze", __name__)

@bp.get("/")
def index():
    return render_template("analyze/index.html")

@bp.post("/analyze")
def analyze():
    text = request.form["texte"]
    text = normalize(text)
    return render_template("analyze/index.html", texte=text)

