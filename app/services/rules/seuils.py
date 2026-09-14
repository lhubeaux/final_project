"""Seuils numériques par langue (D-11).

Une règle ne code jamais un seuil en dur : elle le demande ici. Étendre
l'analyseur à une langue de plus, c'est ajouter une entrée dans ce tableau —
aucun code de règle ne change.
"""

SEUILS: dict[str, dict[str, int]] = {
    "longueur_phrase": {"fr": 25, "en": 21},   # une phrase française est plus longue
}


def seuil(rule_id: str, langue: str) -> int | None:
    """Le seuil de cette règle pour cette langue, ou None s'il n'en existe pas."""
    return SEUILS.get(rule_id, {}).get(langue)
