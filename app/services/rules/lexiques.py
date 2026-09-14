"""Listes de mots par langue (D-12).

Comme les seuils, un lexique est une donnée et non du code : couvrir une langue
de plus, c'est ajouter une entrée dans ce tableau. Chaque expression est associée
à la formulation simple qui la remplace.

Aucune expression ne doit être une sous-chaîne d'une autre sans raison : la règle
arbitre les chevauchements, mais autant lui éviter le travail.
"""

CONNECTEURS_LOURDS: dict[str, dict[str, str]] = {
    "fr": {
        "afin de": "pour",
        "en vue de": "pour",
        "dans le but de": "pour",
        "au moyen de": "avec",
        "par le biais de": "par",
        "dans le cadre de": "pour",
        "en ce qui concerne": "sur",
        "s'agissant de": "sur",
        "au titre de": "selon",
        "en application de": "selon",
        "conformément à": "selon",
        "préalablement à": "avant",
        "à l'issue de": "après",
        "il convient de": "il faut",
        "est susceptible de": "peut",
        "nonobstant": "malgré",
    },
}


def connecteurs_lourds(langue: str) -> dict[str, str]:
    """Le lexique de cette langue, vide si elle n'est pas encore couverte."""
    return CONNECTEURS_LOURDS.get(langue, {})
