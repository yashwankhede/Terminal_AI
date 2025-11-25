"""
Tests for CLI interface
"""

import pytest
from pathlib import Path
from unittest.mock import patch
from terminal_ai.cli import show_star_prompt


def test_show_star_prompt(temp_config_dir):
    """Test star prompt display (should not raise errors)"""
    # Mock the CONFIG_DIR to use the temp directory
    with patch("terminal_ai.config.CONFIG_DIR", temp_config_dir):
        # This should run without errors
        try:
            show_star_prompt()
            assert True
        except Exception as e:
            pytest.fail(f"show_star_prompt raised {e}")
