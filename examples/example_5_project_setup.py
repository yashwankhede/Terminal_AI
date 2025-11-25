#!/usr/bin/env python3
"""
Example 5: Project Setup
Demonstrates automated project setup
"""

from terminal_ai import ask_ai_for_commands, execute_commands_sequence, get_api_key
from terminal_ai.core import extract_commands_from_response

def main():
    """Example of project setup automation"""
    api_key = get_api_key()
    if not api_key:
        print("Error: API key not found")
        return
    
    prompt = "create a new Python project with virtual environment, install Flask and requests, and create a basic app.py"
    print(f"Task: {prompt}\n")
    
    response = ask_ai_for_commands(prompt, api_key)
    commands = extract_commands_from_response(response)
    
    if commands:
        execute_commands_sequence(commands, api_key)
        print("\n✓ Project setup completed!")

if __name__ == "__main__":
    main()

