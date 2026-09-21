import pytest

from app import create_app
from app.cli import amorcer_lexiques
from app.config import TestConfig
from app.models import db


@pytest.fixture
def base_amorcee():
    """Une application de test, base en mémoire amorcée avec les listes de mots.

    Les règles lisent leurs listes en base : sans application, un simple appel à
    `connecteurs_lourds("fr")` lève « Working outside of application context ».
    """
    application = create_app(TestConfig)
    with application.app_context():
        db.create_all()
        amorcer_lexiques()
        yield application
        db.drop_all()


@pytest.fixture
def client(base_amorcee):
    return base_amorcee.test_client()
