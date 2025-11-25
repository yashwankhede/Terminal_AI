#!/usr/bin/env python3
"""
Example 3: System Information
Demonstrates gathering system information
"""

from terminal_ai import ask_ai_for_commands, execute_commands_sequence, get_api_key
from terminal_ai.core import extract_commands_from_response

def main():
    """Example of system information gathering"""
    api_key = get_api_key()
    if not api_key:
        print("Error: API key not found")
        return
    
    prompt = "show me disk usage, top 5 processes by CPU, and network connections"
    print(f"Task: {prompt}\n")
    
    response = ask_ai_for_commands(prompt, api_key)
    commands = extract_commands_from_response(response)
    
    if commands:
        execute_commands_sequence(commands, api_key)

if __name__ == "__main__":
    main()

