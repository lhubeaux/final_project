from flask import Blueprint, render_template, request

from app.services.document import build_document

bp = Blueprint("analyze", __name__)


@bp.route("/", methods=["GET", "POST"])
def index():
    document = None
    if request.method == "POST":
        document = build_document(request.form["texte"])
    return render_template("analyze/index.html", document=document)
