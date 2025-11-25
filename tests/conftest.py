"""
Pytest configuration and fixtures
"""

import pytest
import os
import tempfile
from pathlib import Path


@pytest.fixture
def temp_config_dir(monkeypatch):
    """Create a temporary config directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".terminal_ai"
        config_dir.mkdir()
        monkeypatch.setenv("HOME", str(Path(tmpdir)))
        yield config_dir


@pytest.fixture
def mock_api_key(monkeypatch):
    """Mock API key for testing"""
    test_key = "test-api-key-12345"
    monkeypatch.setenv("OPENAI_API_KEY", test_key)
    return test_key
