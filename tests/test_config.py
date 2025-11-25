"""
Tests for configuration management
"""

import pytest
import tempfile
import os
from pathlib import Path
from terminal_ai.config import load_config, save_config, get_api_key, set_api_key, CONFIG_FILE


def test_load_config_nonexistent():
    """Test loading config when file doesn't exist"""
    # This should return empty dict
    config = load_config()
    assert isinstance(config, dict)


def test_save_and_load_config():
    """Test saving and loading config"""
    test_config = {"api_key": "test-key-123", "setting": "value"}
    save_config(test_config)

    loaded = load_config()
    assert loaded.get("api_key") == "test-key-123"
    assert loaded.get("setting") == "value"


def test_set_and_get_api_key():
    """Test setting and getting API key"""
    test_key = "test-api-key-456"
    set_api_key(test_key)

    retrieved = get_api_key()
    assert retrieved == test_key
