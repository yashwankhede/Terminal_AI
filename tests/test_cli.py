"""
Tests for CLI interface
"""

import pytest
from terminal_ai.cli import show_star_prompt


def test_show_star_prompt():
    """Test star prompt display (should not raise errors)"""
    # This should run without errors
    try:
        show_star_prompt()
        assert True
    except Exception as e:
        pytest.fail(f"show_star_prompt raised {e}")
