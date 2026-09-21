import json
from pathlib import Path

import click

from app.repositories import amorcer_liste

# La source versionnée des listes de mots (D-12). La base n'en est que la copie
# d'exécution : elle se reconstruit toujours depuis ce fichier.
AMORCE = Path(__file__).resolve().parent.parent / "data" / "seeds" / "lexiques.json"


def charger_amorce(chemin: Path = AMORCE) -> dict[str, dict[str, dict[str, str | None]]]:
    """Lit le fichier d'amorce sous une forme unique : {liste: {langue: {expression: remplacement}}}.

    Une liste JSON, comme celle des verbes, devient un dict sans remplacement.
    """
    brut = json.loads(chemin.read_text(encoding="utf-8"))
    return {
        nom: {
            langue: entrees if isinstance(entrees, dict) else dict.fromkeys(entrees)
            for langue, entrees in par_langue.items()
        }
        for nom, par_langue in brut.items()
    }


def amorcer_lexiques(chemin: Path = AMORCE) -> list[tuple[str, str, int, int]]:
    """Charge le fichier d'amorce en base.

    Renvoie, pour chaque liste, son nom, sa langue, le nombre d'entrées ajoutées
    et le nombre d'entrées du fichier.
    """
    bilan = []
    for nom, par_langue in charger_amorce(chemin).items():
        for langue, entrees in par_langue.items():
            ajoutees = amorcer_liste(nom, langue, entrees)
            bilan.append((nom, langue, ajoutees, len(entrees)))
    return bilan


@click.command("seed")
def seed():
    """Charge en base les listes de mots de data/seeds/lexiques.json."""
    for nom, langue, ajoutees, total in amorcer_lexiques():
        click.echo(f"{nom} ({langue}) : {ajoutees} ajoutée(s) sur {total}")
