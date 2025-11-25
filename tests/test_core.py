"""
Tests for core execution functions
"""

import pytest
from terminal_ai.core import extract_commands_from_response, find_controlled_terminal_for_command


def test_extract_commands_from_response():
    """Test command extraction from AI response"""
    response = """Here are the commands:
```bash
ls -la
cd /tmp
echo hello
```"""
    commands = extract_commands_from_response(response)
    assert len(commands) == 3
    assert commands[0]["command"] == "ls -la"
    assert commands[0]["type"] == "execute"


def test_extract_commands_with_new_terminal():
    """Test extraction of NEW_TERMINAL directives"""
    response = """```bash
NEW_TERMINAL: nmap -sC -sV 10.0.0.1
ls -la
```"""
    commands = extract_commands_from_response(response)
    assert len(commands) == 2
    assert commands[0]["type"] == "new_terminal"
    assert commands[1]["type"] == "execute"


def test_find_controlled_terminal_for_command():
    """Test finding controlled terminal for command"""
    command_history = [
        {
            "command": "msfconsole",
            "controlled": True,
            "interactive": True,
            "terminal_id": "term_123",
        }
    ]

    terminal_id = find_controlled_terminal_for_command(
        "use exploit/windows/smb/ms17_010", command_history
    )
    assert terminal_id == "term_123"

    terminal_id = find_controlled_terminal_for_command("ls -la", command_history)
    assert terminal_id is None
