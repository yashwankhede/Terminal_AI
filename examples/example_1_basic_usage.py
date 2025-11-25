#!/usr/bin/env python3
"""
Example 1: Basic Usage
Demonstrates how to use Terminal_AI programmatically for simple tasks
"""

from terminal_ai import ask_ai_for_commands, execute_commands_sequence, get_api_key

def main():
    """Basic example of using Terminal_AI"""
    # Get API key
    api_key = get_api_key()
    if not api_key:
        print("Error: API key not found. Set it using: terminal-ai --set-api-key YOUR_KEY")
        return
    
    # Ask AI for commands
    prompt = "list all Python files in the current directory"
    print(f"Prompt: {prompt}\n")
    
    response = ask_ai_for_commands(prompt, api_key)
    print(f"AI Response:\n{response}\n")
    
    # Extract and execute commands
    from terminal_ai.core import extract_commands_from_response
    commands = extract_commands_from_response(response)
    
    if commands:
        print("Executing commands...\n")
        execute_commands_sequence(commands, api_key)
    else:
        print("No commands to execute")

if __name__ == "__main__":
    main()

