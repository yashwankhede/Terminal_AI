#!/usr/bin/env python3
"""
Example 2: File Operations
Demonstrates file management tasks with Terminal_AI
"""

from terminal_ai import ask_ai_for_commands, execute_commands_sequence, get_api_key
from terminal_ai.core import extract_commands_from_response

def main():
    """Example of file operations"""
    api_key = get_api_key()
    if not api_key:
        print("Error: API key not found")
        return
    
    # Create a backup task
    prompt = "create a backup directory called 'backup' and copy all .txt files there"
    print(f"Task: {prompt}\n")
    
    response = ask_ai_for_commands(prompt, api_key)
    commands = extract_commands_from_response(response)
    
    if commands:
        execute_commands_sequence(commands, api_key)
        print("\n✓ File operations completed!")

if __name__ == "__main__":
    main()

