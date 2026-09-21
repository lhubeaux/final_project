from flask import Blueprint, render_template, request, current_app

from collections import Counter

from app.services.document import build_document
from app.services.extraction import ExtractionError, extensions_supportees, extraire
from app.services.rendering import surligner
from app.services.rules import regles, run

bp = Blueprint("analyze", __name__)

def page(document=None, findings=None, texte_surligne=None, resume=None, erreur=None):
    """Rendu unique de la page d'analyse.

    La route et le gestionnaire d'erreur passent tous deux par ici : la liste
    des formats vient toujours du registre, jamais du gabarit.
    """
    return render_template(
        "analyze/index.html",
        document=document,
        findings=findings or [],
        texte_surligne=texte_surligne,
        resume=resume or [],
        erreur=erreur,
        extensions=extensions_supportees(),
    )


@bp.app_errorhandler(413)
def envoi_trop_volumineux(_echec):
    """Flask refuse la requête avant de la router : `index()` n'est pas appelée.

    `app_errorhandler` et non `errorhandler` : un 413 levé à la lecture du corps
    n'appartient à aucun blueprint. Le code 413 est conservé — rien n'a été
    analysé, répondre 200 mentirait au navigateur.
    """
    plafond = current_app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
    return page(erreur=f"Envoi trop volumineux : {plafond} Mo maximum."), 413



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
