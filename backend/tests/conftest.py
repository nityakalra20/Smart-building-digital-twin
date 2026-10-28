import os
import sys

import pytest

# Let the tests import app.py, simulator.py and storage.py from the backend folder.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402


@pytest.fixture
def app(tmp_path):
    """A Flask app that uses a temporary CSV file, a fixed random seed and no
    background thread, so every test starts clean and gives repeatable results."""
    return create_app(csv_path=str(tmp_path / "readings.csv"), seed=42, start_background=False)


@pytest.fixture
def client(app):
    return app.test_client()
