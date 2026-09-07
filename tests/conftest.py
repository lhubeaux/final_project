import pytest

from app import create_app


@pytest.fixture
def client():
    return create_app().test_client()
