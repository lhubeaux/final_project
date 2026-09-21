"""L'écran des listes de mots : ce qu'on y modifie, l'analyse suivante le voit.

Les tests passent par la route, comme un utilisateur. La fixture `client`
repose sur `base_amorcee` : chaque test part des listes d'origine.
"""

from app.models import WordEntry, WordList, db
from app.repositories import lire_liste


def id_liste(nom):
    return db.session.execute(
        db.select(WordList.id).filter_by(nom=nom, langue="fr")
    ).scalar_one()


def id_entree(expression):
    return db.session.execute(
        db.select(WordEntry.id).filter_by(expression=expression)
    ).scalar_one()


def ajouter(client, nom, **champs):
    return client.post(
        f"/listes/{id_liste(nom)}/entrees", data=champs, follow_redirects=True
    ).get_data(as_text=True)


def signale_un_connecteur(client, texte):
    corps = client.post("/", data={"texte": texte}).get_data(as_text=True)
    return "r-connecteurs_lourds" in corps


# --- affichage ---------------------------------------------------------------

def test_la_page_affiche_les_deux_listes(client):
    corps = client.get("/listes/").get_data(as_text=True)

    assert "Connecteurs lourds" in corps
    assert "Verbes conjugués avec être" in corps
    assert "afin de" in corps
    assert "naître" in corps


def test_le_menu_mene_aux_listes(client):
    assert 'href="/listes/"' in client.get("/").get_data(as_text=True)


# --- ajout -------------------------------------------------------------------

def test_un_ajout_s_applique_des_l_analyse_suivante(client):
    """Le point à montrer en démonstration : aucun redémarrage, aucun cache."""
    texte = "À cet égard, le dossier est complet."
    assert not signale_un_connecteur(client, texte)

    corps = ajouter(client, "connecteurs_lourds", expression="à cet égard",
                    remplacement="sur ce point")

    assert "« à cet égard » ajouté." in corps
    assert signale_un_connecteur(client, texte)


def test_l_ajout_redirige_vers_la_liste(client):
    """POST-Redirect-GET : rafraîchir la page ne rejoue pas l'ajout."""
    reponse = client.post(
        f"/listes/{id_liste('connecteurs_lourds')}/entrees",
        data={"expression": "eu égard à", "remplacement": "vu"},
    )

    assert reponse.status_code == 302
    assert reponse.headers["Location"].endswith(f"#liste-{id_liste('connecteurs_lourds')}")


def test_la_saisie_est_normalisee_comme_le_texte(client):
    """Une apostrophe courbe collée depuis Word ne correspondrait jamais au texte."""
    ajouter(client, "connecteurs_lourds", expression="S\u2019il  y a lieu",
            remplacement="si besoin")

    assert "s'il y a lieu" in lire_liste("connecteurs_lourds", "fr")
    assert signale_un_connecteur(client, "Il faudra, s\u2019il y a lieu, statuer.")


def test_un_doublon_est_refuse_meme_en_majuscules(client):
    avant = len(lire_liste("connecteurs_lourds", "fr"))

    corps = ajouter(client, "connecteurs_lourds", expression="  Afin   DE ",
                    remplacement="pour")

    assert "« afin de » est déjà dans la liste." in corps
    assert len(lire_liste("connecteurs_lourds", "fr")) == avant


def test_un_connecteur_sans_remplacement_est_refuse(client):
    corps = ajouter(client, "connecteurs_lourds", expression="à cet égard")

    assert "cette liste demande un remplacement" in corps
    assert "à cet égard" not in lire_liste("connecteurs_lourds", "fr")


def test_une_expression_vide_est_refusee(client):
    """L'assertion évite l'apostrophe, que Jinja échappe en « &#39; »."""
    corps = ajouter(client, "connecteurs_lourds", expression="   ", remplacement="pour")

    assert "expression est vide" in corps


def test_un_verbe_s_ajoute_sans_remplacement(client):
    """Même envoyé, un remplacement est ignoré pour une liste qui n'en a pas."""
    ajouter(client, "verbes_conjugues_avec_etre", expression="apparaître",
            remplacement="ignoré")

    assert lire_liste("verbes_conjugues_avec_etre", "fr")["apparaître"] is None


# --- suppression -------------------------------------------------------------

def test_une_suppression_s_applique_des_l_analyse_suivante(client):
    texte = "Nonobstant les délais, la demande est recevable."
    assert signale_un_connecteur(client, texte)

    corps = client.post(
        f"/listes/entrees/{id_entree('nonobstant')}/supprimer", follow_redirects=True
    ).get_data(as_text=True)

    assert "« nonobstant » supprimé." in corps
    assert not signale_un_connecteur(client, texte)


# --- identifiants inconnus ---------------------------------------------------

def test_liste_ou_entree_inconnue_donne_404(client):
    assert client.post("/listes/999/entrees", data={"expression": "x"}).status_code == 404
    assert client.post("/listes/entrees/999/supprimer").status_code == 404
