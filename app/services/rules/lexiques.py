"""Listes de mots par langue (D-12), lues en base.

La source versionnée est `data/seeds/lexiques.json` ; `flask seed` la charge en
base, et les règles lisent la base. Les deux fonctions gardent leur signature
d'avant : aucune règle n'a eu à changer.

Aucune expression ne doit être une sous-chaîne d'une autre sans raison : la règle
arbitre les chevauchements, mais autant lui éviter le travail.
"""

from app.repositories import lire_liste


def connecteurs_lourds(langue: str) -> dict[str, str]:
    """Le lexique de cette langue, vide si elle n'est pas encore couverte."""
    return lire_liste("connecteurs_lourds", langue)


def verbes_conjugues_avec_etre(langue: str) -> frozenset[str]:
    """Les verbes qui emploient normalement l'auxiliaire être."""
    return frozenset(lire_liste("verbes_conjugues_avec_etre", langue))
