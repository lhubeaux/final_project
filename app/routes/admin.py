from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app import repositories
from app.services.ingestion.normalization import normalize

bp = Blueprint("admin", __name__, url_prefix="/listes")

# Libellé affiché, et si les entrées de la liste portent une reformulation.
# Une liste absente de ce tableau s'affiche sous son nom brut, sans remplacement.
LISTES = {
    "connecteurs_lourds": ("Connecteurs lourds", True),
    "verbes_conjugues_avec_etre": ("Verbes conjugués avec être", False),
}


def nettoyer(saisie: str) -> str:
    """Met une saisie sous la forme du texte que les règles analysent.

    Les règles cherchent les expressions dans le texte NORMALISÉ : une
    apostrophe courbe collée depuis un traitement de texte ne correspondrait
    jamais. On applique donc la même `normalize()` qu'à l'analyse, puis on
    réduit les suites d'espaces à une seule.
    """
    return " ".join(normalize(saisie).split())


@bp.get("/")
def listes():
    return render_template(
        "admin/listes.html",
        listes=repositories.toutes_les_listes(),
        descriptions=LISTES,
    )


@bp.post("/<int:liste_id>/entrees")
def ajouter(liste_id):
    liste = repositories.trouver_liste(liste_id)
    if liste is None:
        abort(404)

    _, avec_remplacement = LISTES.get(liste.nom, (liste.nom, False))
    # Minuscules : la règle ignore la casse, deux casses feraient un doublon.
    expression = nettoyer(request.form.get("expression", "")).lower()
    remplacement = nettoyer(request.form.get("remplacement", "")) or None

    if not expression:
        flash("L'expression est vide.", "erreur")
    elif avec_remplacement and remplacement is None:
        flash(f"« {expression} » : cette liste demande un remplacement.", "erreur")
    elif not repositories.ajouter_entree(
        liste, expression, remplacement if avec_remplacement else None
    ):
        flash(f"« {expression} » est déjà dans la liste.", "erreur")
    else:
        flash(f"« {expression} » ajouté.", "succes")

    # POST-Redirect-GET : un rafraîchissement ne rejoue pas l'ajout.
    return redirect(url_for("admin.listes", _anchor=f"liste-{liste.id}"))


@bp.post("/entrees/<int:entree_id>/supprimer")
def supprimer(entree_id):
    supprimee = repositories.supprimer_entree(entree_id)
    if supprimee is None:
        abort(404)

    expression, liste_id = supprimee
    flash(f"« {expression} » supprimé.", "succes")
    return redirect(url_for("admin.listes", _anchor=f"liste-{liste_id}"))
