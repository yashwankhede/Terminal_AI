"""
Terminal AI - An AI-powered terminal assistant
Capable of executing terminal commands and performing system tasks
"""

__version__ = "0.1.0"
__author__ = "Terminal AI Contributors"

from terminal_ai.config import Colors, get_api_key, set_api_key
from terminal_ai.core import execute_commands_sequence, ask_ai_for_commands
from terminal_ai.cli import interactive_mode, main

__all__ = [
    "Colors",
    "get_api_key",
    "set_api_key",
    "execute_commands_sequence",
    "ask_ai_for_commands",
    "interactive_mode",
    "main",
]
