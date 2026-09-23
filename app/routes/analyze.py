from collections import Counter

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from app import repositories
from app.services.ingestion.document import build_document
from app.services.extraction import ExtractionError, extensions_supportees, extraire
from app.services.rendering import surligner
from app.services.rules import regles, run

bp = Blueprint("analyze", __name__)

NOM_MAX = 100      # longueur maximale du nom d'une analyse enregistrée


def resumer(findings, langue):
    """Compte par règle active, zéros compris."""
    comptes = Counter(finding.rule_id for finding in findings)
    return [(regle.hint, comptes[regle.id]) for regle in regles(langue)]


def page(document=None, findings=(), erreur=None, nom_fichier=None, analyse=None):
    """Rendu unique de la page d'analyse.

    Toutes les routes et le gestionnaire d'erreur passent par ici : le
    surlignage, le résumé et la liste des formats ne sont calculés qu'à un
    seul endroit. `analyse` est renseignée quand on relit une analyse
    enregistrée ; sinon la page propose de l'enregistrer.
    """
    texte_surligne, resume = None, []
    if document is not None:
        texte_surligne = surligner(document.texte, findings)
        resume = resumer(findings, document.langue)
    return render_template(
        "analyze/index.html",
        document=document,
        findings=findings,
        texte_surligne=texte_surligne,
        resume=resume,
        erreur=erreur,
        nom_fichier=nom_fichier,
        analyse=analyse,
        nom_max=NOM_MAX,
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
    """Analyse un texte et l'affiche. Rien n'est enregistré ici."""
    if request.method == "GET":
        return page()

    fichier = request.files.get("fichier")
    try:
        # Le fichier l'emporte sur la zone de texte : c'est le geste le plus explicite.
        if fichier and fichier.filename:
            texte_brut = extraire(fichier.filename, fichier.stream)
        else:
            texte_brut = request.form.get("texte", "")
    except ExtractionError as echec:
        return page(erreur=str(echec))

    maximum = current_app.config["MAX_TEXT_LENGTH"]
    if len(texte_brut) > maximum:
        return page(
            erreur=f"Texte trop long : {len(texte_brut)} caractères pour {maximum} au maximum."
        )
    if not texte_brut.strip():
        return page(erreur="Aucun texte à analyser.")

    document = build_document(texte_brut, langue="fr")
    nom_fichier = fichier.filename if fichier and fichier.filename else None
    return page(document=document, findings=run(document), nom_fichier=nom_fichier)


@bp.get("/analyses/")
def analyses():
    return render_template("analyze/analyses.html", analyses=repositories.toutes_les_analyses())


@bp.post("/analyses/")
def enregistrer():
    """Enregistre, sous le nom choisi, le texte qui vient d'être analysé.

    Le formulaire renvoie le texte normalisé, pas les signalements : on ne se
    fie jamais à des empans venus du navigateur, on relance l'analyse. Comme
    normalize() est idempotente, le texte relu — donc chaque empan — est celui
    qui était affiché. Le navigateur envoie les retours à la ligne en CRLF ;
    normalize() les ramène à LF.
    """
    texte = request.form.get("texte", "")
    nom = " ".join(request.form.get("nom", "").split())
    nom_fichier = request.form.get("nom_fichier") or None

    if not texte.strip() or len(texte) > current_app.config["MAX_TEXT_LENGTH"]:
        abort(400)      # champ caché modifié à la main : ce n'est pas un parcours utilisateur

    document = build_document(texte, langue="fr")
    findings = run(document)
    if not nom or len(nom) > NOM_MAX:
        return page(
            document=document, findings=findings, nom_fichier=nom_fichier,
            erreur=f"Donnez un nom à l'analyse, {NOM_MAX} caractères au maximum.",
        )

    analysis_id = repositories.enregistrer_analyse(nom, document, findings, nom_fichier=nom_fichier)
    flash(f"Analyse « {nom} » enregistrée.", "succes")
    # POST-Redirect-GET : rafraîchir la page ne réenregistre pas l'analyse.
    return redirect(url_for("analyze.relire", analysis_id=analysis_id))


@bp.get("/analyses/<int:analysis_id>")
def relire(analysis_id):
    """Réaffiche une analyse enregistrée, sans relancer les règles."""
    analyse = repositories.lire_analyse(analysis_id)
    if analyse is None:
        abort(404)
    # normalize() est idempotente : le texte relu est inchangé, les empans restent valides.
    document = build_document(analyse.document.texte, langue=analyse.document.langue)
    return page(document=document, findings=analyse.findings, analyse=analyse)
