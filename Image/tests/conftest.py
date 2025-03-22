# tests/conftest.py
import pytest
import tempfile
import os


@pytest.fixture
def app():
    # Create temporary database
    db_fd, db_path = tempfile.mkstemp()

    from app import create_app
    app = create_app({
        'TESTING': True,
        'DATABASE': db_path,
        'GEMINI_API_KEY': 'test-key'  # Mock API key
    })

    yield app

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()
