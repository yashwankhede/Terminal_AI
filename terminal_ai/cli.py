"""
CLI interface for Terminal AI
Handles interactive mode and command-line argument parsing
"""

import sys
import argparse
import time
import logging

# Try to import readline for command history
try:
    import readline

    READLINE_AVAILABLE = True
except ImportError:
    READLINE_AVAILABLE = False

from terminal_ai.config import Colors, CONFIG_DIR, get_api_key, set_api_key, is_first_run
from terminal_ai.core import (
    execute_command_live,
    execute_commands_sequence,
    ask_ai_for_commands,
    ask_ai_for_next_steps,
    extract_commands_from_response,
    find_controlled_terminal_for_command,
    open_new_terminal,
    send_command_to_terminal,
    read_terminal_output,
)
from terminal_ai.utils import (
    type_command,
    is_long_running_command,
    is_interactive_command,
    suggest_non_interactive_alternative,
    is_dangerous_command,
    check_command_exists,
    suggest_alternative,
    extract_subdomains_and_ips,
    add_to_hosts_file,
)

logger = logging.getLogger(__name__)


def show_star_prompt():
    """Show star prompt on first run"""
    if is_first_run():
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.CYAN}If Terminal_AI helped you, consider starring the repo:{Colors.RESET}")
        print(
            f"{Colors.BOLD}{Colors.YELLOW}https://github.com/yashwankhede/Terminal_AI{Colors.RESET}"
        )
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")


def interactive_mode(api_key: str):
    """Interactive mode with live command execution and context awareness"""
    show_star_prompt()

    print(f"{Colors.BOLD}{Colors.CYAN}╔════════════════════════════════════════╗{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}║   Terminal AI - Live Control Mode      ║{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}╚════════════════════════════════════════╝{Colors.RESET}")
    print(f"\n{Colors.YELLOW}I'm ready to execute commands in your terminal!{Colors.RESET}")
    print(f"{Colors.YELLOW}I'll remember previous commands and their outputs.{Colors.RESET}")
    print(f"{Colors.YELLOW}Type 'exit' or 'quit' to leave, 'help' for commands\n{Colors.RESET}")

    # Set up readline for command history
    history_file = CONFIG_DIR / "command_history.txt"
    if READLINE_AVAILABLE:
        try:
            # Load history if it exists
            if history_file.exists():
                readline.read_history_file(str(history_file))
            # Set history length
            readline.set_history_length(1000)
        except Exception as e:
            logger.debug(f"Error loading readline history: {e}")

    # Command history for context
    command_history = []

    while True:
        try:
            user_input = input(f"{Colors.GREEN}terminal-ai>{Colors.RESET} ").strip()

            # Save to readline history
            if READLINE_AVAILABLE and user_input:
                try:
                    readline.add_history(user_input)
                    readline.write_history_file(str(history_file))
                except Exception as e:
                    logger.debug(f"Error saving readline history: {e}")

            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit"]:
                print(f"{Colors.CYAN}Goodbye!{Colors.RESET}")
                break

            if user_input.lower() == "help":
                print(f"\n{Colors.BOLD}Commands:{Colors.RESET}")
                print("  exit/quit - Exit the program")
                print("  help - Show this help message")
                print("  execute <command> - Execute a command directly")
                print("  history - Show recent command history")
                print("  clear - Clear command history")
                print("\nOr just describe what you want and I'll do it!\n")
                continue

            if user_input.lower() == "history":
                if command_history:
                    print(f"\n{Colors.BOLD}Recent Command History:{Colors.RESET}\n")
                    for i, entry in enumerate(command_history[-10:], 1):
                        print(f"{i}. {entry.get('command', 'N/A')}")
                        print(f"   Exit Code: {entry.get('exit_code', 'N/A')}")
                        output = entry.get("output", "")
                        if output and len(output) > 100:
                            print(f"   Output: {output[:100]}...")
                        elif output:
                            print(f"   Output: {output}")
                        print()
                else:
                    print(f"{Colors.YELLOW}No command history yet.{Colors.RESET}\n")
                continue

            if user_input.lower() == "clear":
                command_history.clear()
                print(f"{Colors.GREEN}Command history cleared.{Colors.RESET}\n")
                continue

            if user_input.startswith("execute "):
                cmd = user_input[8:].strip()
                exit_code, output = execute_command_live(cmd, capture_output=True)

                # Extract subdomains/domains and add to /etc/hosts
                subdomains = extract_subdomains_and_ips(output)
                for subdomain_info in subdomains:
                    domain = subdomain_info["domain"]
                    ip = subdomain_info["ip"]
                    if add_to_hosts_file(domain, ip):
                        print(f"{Colors.GREEN}✓ Added {domain} -> {ip} to /etc/hosts{Colors.RESET}")
                    else:
                        print(
                            f"{Colors.YELLOW}⚠️  Could not add {domain} to /etc/hosts (may need sudo){Colors.RESET}"
                        )

                command_history.append(
                    {
                        "command": cmd,
                        "exit_code": exit_code,
                        "output": output,
                        "type": "execute",
                        "subdomains_found": subdomains,
                    }
                )
                print()
                continue

            # Get commands from AI with context
            print(
                f"\n{Colors.BLUE}🤔 Processing your request (with context from {len(command_history)} previous commands)...{Colors.RESET}\n"
            )
            response = ask_ai_for_commands(user_input, api_key, command_history=command_history)

            if not response:
                print(f"{Colors.RED}No response from AI.{Colors.RESET}\n")
                continue

            # Extract commands
            commands = extract_commands_from_response(response)

            if commands:
                # Execute commands using the core execution function
                command_history = execute_commands_sequence(commands, api_key, command_history)

                # After executing all commands, intelligently suggest next steps
                print(
                    f"{Colors.BOLD}{Colors.MAGENTA}🧠 Analyzing results and determining next steps...{Colors.RESET}\n"
                )
                next_commands = ask_ai_for_next_steps(api_key, command_history, max_iterations=3)

                iteration = 0
                max_auto_iterations = 3  # Limit automatic iterations

                while next_commands and iteration < max_auto_iterations:
                    iteration += 1
                    print(
                        f"{Colors.CYAN}💡 Suggested next steps (iteration {iteration}/{max_auto_iterations}):{Colors.RESET}\n"
                    )

                    # Execute suggested commands
                    command_history = execute_commands_sequence(
                        next_commands, api_key, command_history
                    )

                    # Ask for next steps again
                    if iteration < max_auto_iterations:
                        print(
                            f"{Colors.BOLD}{Colors.MAGENTA}🧠 Analyzing latest results...{Colors.RESET}\n"
                        )
                        next_commands = ask_ai_for_next_steps(
                            api_key, command_history, max_iterations=2
                        )
                    else:
                        break

                if iteration > 0:
                    print(
                        f"{Colors.GREEN}✓ Completed {iteration} iteration(s) of intelligent next-step suggestions{Colors.RESET}"
                    )
                    print(
                        f"{Colors.CYAN}💡 You can continue manually or ask for more steps{Colors.RESET}\n"
                    )
            else:
                # If no commands extracted, show the response
                print(f"{Colors.CYAN}AI Response:{Colors.RESET}")
                print(response)
                print()

        except KeyboardInterrupt:
            print(f"\n\n{Colors.CYAN}Goodbye!{Colors.RESET}")
            break
        except EOFError:
            print(f"\n\n{Colors.CYAN}Goodbye!{Colors.RESET}")
            break


def main():
    """Main entry point for Terminal AI"""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(
        description="Terminal AI - AI-powered terminal assistant with live execution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  terminal-ai "list all files in current directory"
  terminal-ai "create a new Python project"
  terminal-ai --interactive
        """,
    )

    parser.add_argument("prompt", nargs="?", help="Your task or question")

    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Start interactive mode (default if no prompt)",
    )

    parser.add_argument("--set-api-key", help="Set OpenAI API key")

    # Check for common typos before parsing
    for arg in sys.argv:
        if arg in ["--interactivel", "--interactiv", "--interactve", "--interactie"]:
            print(f"{Colors.YELLOW}⚠️  Did you mean --interactive (or -i)?{Colors.RESET}")
            print(f"{Colors.CYAN}Usage: terminal-ai --interactive{Colors.RESET}")
            print(f"{Colors.CYAN}   or: terminal-ai -i{Colors.RESET}")
            sys.exit(1)

    args = parser.parse_args()

    # Handle API key setting
    if args.set_api_key:
        set_api_key(args.set_api_key)
        print("API key saved successfully!")
        return

    # Get API key
    api_key = get_api_key()
    if not api_key:
        print("Error: OpenAI API key not found!")
        print("Please set it using: terminal-ai --set-api-key YOUR_API_KEY")
        print("Or run the installation script: ./install.sh")
        sys.exit(1)

    # Interactive mode
    if args.interactive or not args.prompt:
        interactive_mode(api_key)
        return

    # Single query mode
    show_star_prompt()
    print(f"\n{Colors.BLUE}🤔 Processing your request...{Colors.RESET}\n")
    command_history = []
    response = ask_ai_for_commands(args.prompt, api_key, command_history=command_history)

    if not response:
        print(f"{Colors.RED}No response from AI.{Colors.RESET}")
        return

    # Extract and execute commands
    commands = extract_commands_from_response(response)

    if commands:
        execute_commands_sequence(commands, api_key, command_history)
    else:
        # If no commands extracted, show the response
        print(response)


if __name__ == "__main__":
    main()
