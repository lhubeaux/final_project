import pytest

from app import create_app
from app.config import TestConfig
from app.models import db


@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()
