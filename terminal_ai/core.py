"""
Core execution logic for Terminal AI
Handles command execution, terminal control, and AI interaction
"""

import os
import sys
import re
import subprocess
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from terminal_ai.config import Colors, CONFIG_DIR
from terminal_ai.utils import (
    type_command,
    is_long_running_command,
    is_interactive_command,
    suggest_non_interactive_alternative,
    is_dangerous_command,
    check_command_exists,
    find_wordlists,
    get_available_wordlists_info,
    extract_subdomains_and_ips,
    add_to_hosts_file,
    get_available_tools,
    suggest_alternative,
    get_system_info,
    extract_ssh_credentials,
    convert_ssh_to_sshpass,
)

# Try to import interactive handler
try:
    from terminal_ai.interactive import execute_command_interactive, PEXPECT_AVAILABLE
    INTERACTIVE_HANDLER_AVAILABLE = PEXPECT_AVAILABLE
except ImportError:
    INTERACTIVE_HANDLER_AVAILABLE = False
    execute_command_interactive = None

logger = logging.getLogger(__name__)

# Global dictionary to track controlled terminals
controlled_terminals: Dict[str, Dict[str, Any]] = {}


def execute_command_live(
    command: str,
    shell: bool = True,
    show_command: bool = True,
    timeout: int = 300,
    capture_output: bool = True,
    api_key: Optional[str] = None,
    user_context: str = "",
    command_history: Optional[List[Dict[str, Any]]] = None,
    use_interactive: bool = True,
) -> Tuple[int, str]:
    """
    Execute a terminal command with live output streaming
    If use_interactive=True and command is interactive, uses pexpect for automatic prompt handling
    Returns: (exit_code, output)
    """
    # Use interactive handler if available and command is interactive
    if (
        use_interactive
        and INTERACTIVE_HANDLER_AVAILABLE
        and execute_command_interactive
        and is_interactive_command(command)
        and api_key
    ):
        logger.info("Using interactive handler for command")
        return execute_command_interactive(
            command,
            api_key,
            user_context=user_context,
            command_history=command_history,
            timeout=timeout,
            show_command=show_command,
        )
    
    if show_command:
        type_command(command)

    output_lines = []
    last_output_time = None
    prompt_count = 0
    process = None

    try:
        # Use Popen for real-time output
        process = subprocess.Popen(
            command,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        logger.info(f"Executing command: {command}")

        # Stream output in real-time
        start_time = time.time()
        while True:
            output = process.stdout.readline()
            if output == "" and process.poll() is not None:
                break
            if output:
                print(output, end="", flush=True)
                if capture_output:
                    output_lines.append(output)
                last_output_time = time.time()

                # Detect interactive prompts (like msf6 >, mysql>, etc.)
                if re.search(
                    r"(msf\d+\s*>|mysql>\s*|psql>\s*|>>>\s*|In \[\d+\]:\s*)$", output.strip()
                ):
                    prompt_count += 1
                    # If we see multiple prompts with no other output, likely waiting for input
                    if prompt_count >= 3:
                        logger.warning("Detected interactive prompt, terminating")
                        print(
                            f"\n{Colors.YELLOW}⚠️  Detected interactive prompt. Command appears to be waiting for input.{Colors.RESET}"
                        )
                        print(
                            f"{Colors.YELLOW}Terminating and opening in new terminal instead...{Colors.RESET}"
                        )
                        process.terminate()
                        return (130, "".join(output_lines))

            # Check for no output for too long (might be waiting for input)
            if (
                last_output_time
                and (time.time() - last_output_time > 10)
                and process.poll() is None
            ):
                # Check if process is still running but producing no output
                if is_interactive_command(command):
                    logger.warning("No output for 10s, command may be waiting for input")
                    print(
                        f"\n{Colors.YELLOW}⚠️  No output for 10s. Command may be waiting for input.{Colors.RESET}"
                    )
                    print(
                        f"{Colors.YELLOW}Terminating and opening in new terminal instead...{Colors.RESET}"
                    )
                    process.terminate()
                    return (130, "".join(output_lines))

            # Check timeout
            if time.time() - start_time > timeout:
                logger.warning(f"Command timeout after {timeout}s")
                print(
                    f"\n{Colors.YELLOW}⚠️  Command timeout after {timeout}s. Continuing...{Colors.RESET}"
                )
                process.terminate()
                break

        return_code = process.poll()
        logger.info(f"Command completed with exit code: {return_code}")
        return (return_code if return_code is not None else 0, "".join(output_lines))
    except KeyboardInterrupt:
        logger.info("Command interrupted by user")
        print(f"\n{Colors.YELLOW}Command interrupted by user{Colors.RESET}")
        if process:
            try:
                process.terminate()
            except:
                pass
        return (130, "".join(output_lines))
    except Exception as e:
        error_msg = f"Error executing command: {str(e)}"
        logger.error(error_msg)
        print(f"{Colors.RED}{error_msg}{Colors.RESET}")
        return (1, error_msg)


def execute_command_safe(command: str, shell: bool = True) -> Tuple[str, int]:
    """
    Execute a terminal command safely (for quick checks)
    Returns: (output, exit_code)
    """
    try:
        result = subprocess.run(command, shell=shell, capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        return output, result.returncode
    except subprocess.TimeoutExpired:
        logger.warning("Command timed out")
        return "Command timed out", 1
    except Exception as e:
        logger.error(f"Error in safe command execution: {e}")
        return f"Error: {str(e)}", 1


def create_terminal_control_system(terminal_id: str) -> Dict[str, Path]:
    """Create control files for a terminal session"""
    control_dir = CONFIG_DIR / "terminal_controls"
    control_dir.mkdir(exist_ok=True)

    control_files = {
        "command_file": control_dir / f"{terminal_id}_commands.txt",
        "output_file": control_dir / f"{terminal_id}_output.txt",
        "status_file": control_dir / f"{terminal_id}_status.txt",
        "pid_file": control_dir / f"{terminal_id}_pid.txt",
    }

    # Initialize files
    for file_path in control_files.values():
        if file_path.exists():
            file_path.unlink()
        file_path.touch()

    logger.debug(f"Created terminal control system for {terminal_id}")
    return control_files


def get_terminal_wrapper_script(
    control_files: Dict[str, Path], initial_command: Optional[str] = None, ssh_password: Optional[str] = None
) -> str:
    """Generate a wrapper script that reads commands from control file"""
    cmd_file = control_files["command_file"]
    out_file = control_files["output_file"]
    status_file = control_files["status_file"]

    # Escape paths for bash
    cmd_file_str = str(cmd_file).replace("'", "'\\''")
    out_file_str = str(out_file).replace("'", "'\\''")
    status_file_str = str(status_file).replace("'", "'\\''")

    # Check if initial command is SSH
    is_ssh = initial_command and "ssh" in initial_command.lower() and "@" in initial_command
    
    if is_ssh:
        # For SSH, use expect to handle the interactive session
        # Extract SSH details
        import re
        match = re.search(r"ssh\s+([^\s@]+)@([^\s]+)", initial_command, re.IGNORECASE)
        if match:
            ssh_user = match.group(1)
            ssh_host = match.group(2)
            # Extract password if available (from sshpass, parameter, or context)
            password = ssh_password or ""
            if not password and "sshpass" in initial_command.lower():
                # Try to extract password from sshpass command
                pass_match = re.search(r"sshpass\s+-p\s+['\"]?([^'\"]+)['\"]?", initial_command, re.IGNORECASE)
                if pass_match:
                    password = pass_match.group(1)
            
            # Escape password for expect (escape special characters)
            if password:
                # Escape for expect: escape $, [, ], {, }, \, ", and spaces
                escaped_password = password.replace("\\", "\\\\").replace("$", "\\$").replace("[", "\\[").replace("]", "\\]").replace("{", "\\{").replace("}", "\\}").replace('"', '\\"')
            else:
                escaped_password = ""
            
            # Escape initial command for expect
            escaped_ssh_cmd = initial_command.replace('"', '\\"').replace('$', '\\$')
            newline_char = "\\n"
            return_char = "\\r"
            
            # Set password variable in expect script (must be set before use)
            if escaped_password:
                password_set_cmd = f'set password "{escaped_password}"'
            else:
                password_set_cmd = 'set password ""'
            
            wrapper = f"""#!/usr/bin/expect -f
# Terminal AI Control Wrapper for SSH
# Uses expect to handle SSH interactive session

set timeout 30
set CMD_FILE "{cmd_file_str}"
set OUT_FILE "{out_file_str}"
set STATUS_FILE "{status_file_str}"

# Set password variable
{password_set_cmd}

# Open output file
set out_fd [open "$OUT_FILE" a]

proc log_output {{msg}} {{
    global out_fd
    puts $out_fd "[clock seconds] $msg"
    flush $out_fd
}}

# Write status
set status_fd [open "$STATUS_FILE" w]
puts $status_fd "READY"
close $status_fd

# Error handling proc
proc handle_error {{msg}} {{
    global STATUS_FILE OUT_FILE
    set status_fd [open "$STATUS_FILE" w]
    puts $status_fd "ERROR: $msg"
    close $status_fd
    set out_fd [open "$OUT_FILE" a]
    puts $out_fd "[clock seconds] ERROR: $msg"
    close $out_fd
    exit 1
}}

# Spawn SSH connection
log_output "Spawning SSH: {escaped_ssh_cmd}"
if {{[catch {{spawn -noecho bash -c "{escaped_ssh_cmd}"}} error]}} {{
    handle_error "Failed to spawn SSH: $error"
}}

# Enable logging of all expect interactions
log_user 0
exp_internal 0

# Handle password prompt if needed
if {{$password != ""}} {{
    expect {{
        "password:" {{
            send "$password{return_char}"
            exp_continue
        }}
        "Password:" {{
            send "$password{return_char}"
            exp_continue
        }}
        -re {{.*@.*[:\$] }} {{
            # SSH prompt detected
            log_output "SSH connected successfully"
        }}
        timeout {{
            log_output "Timeout waiting for SSH prompt - trying without password"
            # Try to continue anyway
        }}
    }}
}} else {{
    expect {{
        "password:" {{
            log_output "Password prompt detected but no password provided"
            # Wait a bit and continue
            sleep 2
        }}
        "Password:" {{
            log_output "Password prompt detected but no password provided"
            sleep 2
        }}
        -re ".*@.*[:$] " {{
            log_output "SSH connected successfully"
        }}
        timeout {{
            log_output "Timeout waiting for SSH prompt"
            # Don't exit, try to continue
        }}
    }}
}}

# Check if spawn was successful
if {{$spawn_id == 0}} {{
    handle_error "SSH spawn failed"
}}

# Main loop - read commands from control file and send to SSH
set LAST_LINE_COUNT 0
while {{1}} {{
    if {{[file exists "$CMD_FILE"]}} {{
        set fd [open "$CMD_FILE" r]
        set lines [split [read $fd] "{newline_char}"]
        close $fd
        
        set CURRENT_LINE_COUNT [llength $lines]
        if {{$CURRENT_LINE_COUNT > $LAST_LINE_COUNT}} {{
            for {{set i $LAST_LINE_COUNT}} {{$i < $CURRENT_LINE_COUNT}} {{incr i}} {{
                set line [string trim [lindex $lines $i]]
                if {{$line != ""}} {{
                    log_output "Sending command: $line"
                    send "$line{return_char}"
                    
                    # Capture all output until we get the prompt back
                    set cmd_timeout 30
                    expect {{
                        -re {{(.*)\r\n.*@.*[:\$] }} {{
                            # Command completed, got prompt back
                            # Capture everything before the prompt (group 1)
                            set cmd_output $expect_out(1,string)
                            # Write the actual command output
                            if {{$cmd_output != ""}} {{
                                puts $out_fd "$cmd_output"
                                flush $out_fd
                            }}
                            log_output "Command completed"
                        }}
                        -re {{.*@.*[:\$] }} {{
                            # Got prompt - capture everything in buffer before prompt
                            set full_buffer $expect_out(buffer)
                            # Extract everything before the prompt line
                            if {{[regexp {{(.*)\r\n.*@.*[:\$] }} $full_buffer match output_part]}} {{
                                if {{$output_part != ""}} {{
                                    puts $out_fd "$output_part"
                                    flush $out_fd
                                }}
                            }} else {{
                                # No output before prompt, just log
                                log_output "Command completed (no output)"
                            }}
                        }}
                        timeout {{
                            log_output "Timeout waiting for command completion"
                            # Try to capture what we have so far
                            set cmd_output $expect_out(buffer)
                            if {{$cmd_output != ""}} {{
                                puts $out_fd "$cmd_output"
                                flush $out_fd
                            }}
                        }}
                    }} timeout $cmd_timeout
                }}
            }}
            set LAST_LINE_COUNT $CURRENT_LINE_COUNT
        }}
    }}
    sleep 0.5
}}

close $out_fd
"""
        else:
            # Fallback to regular wrapper if SSH parsing fails
            is_ssh = False
    
    if not is_ssh:
        # Regular wrapper for non-SSH commands
        # Escape initial command for bash
        if initial_command:
            escaped_init_cmd = initial_command.replace("'", "'\\''")
            init_cmd_part = f'execute_command "{escaped_init_cmd}"'
        else:
            init_cmd_part = ""

        wrapper = f"""#!/bin/bash
# Terminal AI Control Wrapper
# This script reads commands from control file and executes them

CMD_FILE="{cmd_file_str}"
OUT_FILE="{out_file_str}"
STATUS_FILE="{status_file_str}"

# Function to execute command and capture output
execute_command() {{
    local cmd="$1"
    echo "[$(date +%s)] Executing: $cmd" >> "$OUT_FILE"
    # Execute command and capture both stdout and stderr
    eval "$cmd" >> "$OUT_FILE" 2>&1
    local exit_code=$?
    echo "[$(date +%s)] Exit code: $exit_code" >> "$OUT_FILE"
    echo "---" >> "$OUT_FILE"
    return $exit_code
}}

# Write initial status
echo "READY" > "$STATUS_FILE"

# Execute initial command if provided
{init_cmd_part}

# Main loop - read commands from control file
LAST_LINE_COUNT=0
while true; do
    if [ -f "$CMD_FILE" ]; then
        CURRENT_LINE_COUNT=$(wc -l < "$CMD_FILE" 2>/dev/null || echo "0")
        if [ "$CURRENT_LINE_COUNT" -gt "$LAST_LINE_COUNT" ]; then
            # Read new lines
            tail -n +$((LAST_LINE_COUNT + 1)) "$CMD_FILE" | while IFS= read -r line || [ -n "$line" ]; do
                if [ -n "$line" ] && [ "$line" != "" ]; then
                    execute_command "$line"
                fi
            done
            LAST_LINE_COUNT=$CURRENT_LINE_COUNT
        fi
    fi
    sleep 0.5
done
"""
    
    return wrapper


def open_new_terminal(
    command: Optional[str] = None,
    split: bool = False,
    output_file: Optional[str] = None,
    terminal_id: Optional[str] = None,
    ssh_password: Optional[str] = None,
) -> str:
    """
    Open a new terminal window with AI control capability
    Returns terminal_id for future control
    """
    if terminal_id is None:
        terminal_id = f"term_{int(time.time())}_{os.getpid()}"

    # Create control system
    control_files = create_terminal_control_system(terminal_id)

    # Generate wrapper script (pass ssh_password if provided)
    wrapper_script = get_terminal_wrapper_script(control_files, command, ssh_password=ssh_password)
    
    # Determine file extension and executor based on whether it's expect or bash
    is_ssh = command and "ssh" in command.lower() and "@" in command
    if is_ssh:
        wrapper_file = control_files["command_file"].parent / f"{terminal_id}_wrapper.exp"
        wrapper_exec = "expect"
    else:
        wrapper_file = control_files["command_file"].parent / f"{terminal_id}_wrapper.sh"
        wrapper_exec = "bash"

    with open(wrapper_file, "w") as f:
        f.write(wrapper_script)
    os.chmod(wrapper_file, 0o755)

    # Command to run in new terminal
    # Add error handling wrapper
    if is_ssh:
        # Check if expect is available, if not fall back
        try:
            result = subprocess.run(["which", "expect"], capture_output=True, timeout=2, check=False)
            if result.returncode != 0:
                logger.warning("expect not found, using bash wrapper instead")
                # Regenerate as bash wrapper
                wrapper_script = get_terminal_wrapper_script(control_files, command, ssh_password=None)
                wrapper_file = control_files["command_file"].parent / f"{terminal_id}_wrapper.sh"
                wrapper_exec = "bash"
                with open(wrapper_file, "w") as f:
                    f.write(wrapper_script)
                os.chmod(wrapper_file, 0o755)
                is_ssh = False
        except Exception as e:
            logger.warning(f"Error checking expect: {e}, using bash wrapper")
            wrapper_script = get_terminal_wrapper_script(control_files, command, ssh_password=None)
            wrapper_file = control_files["command_file"].parent / f"{terminal_id}_wrapper.sh"
            wrapper_exec = "bash"
            with open(wrapper_file, "w") as f:
                f.write(wrapper_script)
            os.chmod(wrapper_file, 0o755)
            is_ssh = False
    
    terminal_command = f"{wrapper_exec} {wrapper_file}"

    if sys.platform == "darwin":
        # macOS - try to detect terminal app
        terminal_app = os.getenv("TERM_PROGRAM", "Terminal")

        # Escape command for AppleScript
        escaped_cmd = terminal_command.replace("\\", "\\\\").replace('"', '\\"')

        if terminal_app == "iTerm.app" or "iTerm" in terminal_app:
            # iTerm2 - get window ID
            script = f"""
            tell application "iTerm"
                set newWindow to (create window with default profile)
                set windowId to id of newWindow
                tell current session of newWindow
                    write text "{escaped_cmd}"
                end tell
                return windowId
            end tell
            """
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            window_id = result.stdout.strip()
        else:
            # Terminal.app - get window ID
            script = f"""
            tell application "Terminal"
                set newTab to (do script "{escaped_cmd}")
                set windowId to id of window 1 whose selected tab is newTab
                activate
                return windowId as string
            end tell
            """
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            window_id = result.stdout.strip()

        # Store terminal info
        controlled_terminals[terminal_id] = {
            "window_id": window_id,
            "control_files": control_files,
            "wrapper_file": wrapper_file,
            "status": "active",
        }

    elif sys.platform.startswith("linux"):
        # Linux - use tmux or screen for control
        terminals = ["gnome-terminal", "konsole", "xterm", "terminator"]
        for term in terminals:
            if subprocess.run(["which", term], capture_output=True).returncode == 0:
                subprocess.Popen([term, "-e", "bash", "-c", terminal_command + "; exec bash"])
                break

        controlled_terminals[terminal_id] = {
            "control_files": control_files,
            "wrapper_file": wrapper_file,
            "status": "active",
        }

    logger.info(f"Opened new terminal: {terminal_id}")
    return terminal_id


def send_command_to_terminal(terminal_id: str, command: str) -> bool:
    """Send a command to a controlled terminal"""
    if terminal_id not in controlled_terminals:
        logger.warning(f"Terminal {terminal_id} not found")
        return False

    control_files = controlled_terminals[terminal_id]["control_files"]
    command_file = control_files["command_file"]

    try:
        with open(command_file, "a") as f:
            f.write(command + "\n")
        logger.debug(f"Sent command to terminal {terminal_id}: {command}")
        return True
    except Exception as e:
        logger.error(f"Error sending command to terminal: {e}")
        return False


def read_terminal_output(terminal_id: str) -> str:
    """Read output from a controlled terminal"""
    if terminal_id not in controlled_terminals:
        return ""

    control_files = controlled_terminals[terminal_id]["control_files"]
    output_file = control_files["output_file"]

    try:
        if output_file.exists():
            with open(output_file, "r") as f:
                return f.read()
    except Exception as e:
        logger.error(f"Error reading terminal output: {e}")

    return ""


def get_terminal_status(terminal_id: str) -> str:
    """Get status of a controlled terminal"""
    if terminal_id not in controlled_terminals:
        return "not_found"

    control_files = controlled_terminals[terminal_id]["control_files"]
    status_file = control_files["status_file"]

    try:
        if status_file.exists():
            with open(status_file, "r") as f:
                return f.read().strip()
    except Exception as e:
        logger.error(f"Error reading terminal status: {e}")

    return "unknown"


def read_terminal_output_file(output_file: str, timeout: int = 5) -> str:
    """Read output from a terminal output file (legacy function)"""
    if not os.path.exists(output_file):
        return ""

    try:
        with open(output_file, "r") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading output file: {e}")
        return ""


def check_parallel_outputs(command_history: List[Dict[str, Any]]) -> None:
    """Check and update command history with output from parallel terminals"""
    for entry in command_history:
        # Check for new terminal control system
        if entry.get("terminal_id"):
            terminal_id = entry.get("terminal_id")
            output = read_terminal_output(terminal_id)
            if output and output != entry.get("output", ""):
                entry["output"] = output
                # Try to detect if command completed
                if (
                    "Nmap done" in output
                    or "completed" in output.lower()
                    or "finished" in output.lower()
                ):
                    entry["exit_code"] = 0
                    entry["completed"] = True
        # Legacy support for output_file
        elif entry.get("parallel") and entry.get("output_file"):
            output_file = entry.get("output_file")
            if os.path.exists(output_file):
                # Read the output
                output = read_terminal_output_file(output_file)
                if output and output != entry.get("output", ""):
                    # Update the entry with new output
                    entry["output"] = output
                    # Try to detect if command completed
                    if (
                        "Nmap done" in output
                        or "completed" in output.lower()
                        or "finished" in output.lower()
                    ):
                        entry["exit_code"] = 0
                        entry["completed"] = True


def find_controlled_terminal_for_command(
    command: str, command_history: List[Dict[str, Any]]
) -> Optional[str]:
    """Find an existing controlled terminal that can handle this command"""
    command_lower = command.lower()

    # Check if command is for an interactive program that's already running
    if (
        "msfconsole" in command_lower
        or "use " in command_lower
        or "set " in command_lower
        or "run" == command_lower.strip()
    ):
        # Look for existing msfconsole terminal
        for entry in reversed(command_history):
            if entry.get("controlled") and entry.get("interactive"):
                if "msfconsole" in entry.get("command", "").lower():
                    return entry.get("terminal_id")
    
    # Check if command should go to an SSH session
    # If there's an active SSH terminal, route most commands there
    ssh_terminal = None
    for entry in reversed(command_history):
        if entry.get("controlled") and entry.get("terminal_id"):
            cmd = entry.get("command", "").lower()
            # Check if this is an SSH terminal
            if "ssh" in cmd and "@" in cmd:
                ssh_terminal = entry.get("terminal_id")
                ssh_host = None
                # Extract host from SSH command
                import re
                match = re.search(r"ssh\s+[^\s@]+@([^\s]+)", cmd)
                if match:
                    ssh_host = match.group(1)
                break
    
    # If we have an SSH terminal, check if command should go there
    if ssh_terminal:
        # Commands that should ALWAYS go to SSH (file operations, system commands, etc.)
        ssh_commands = [
            "find", "grep", "cat", "ls", "cd", "pwd", "whoami", "id",
            "ps", "netstat", "ss", "ifconfig", "ip", "uname", "hostname",
            "sudo", "su", "python", "python3", "bash", "sh", "nc", "netcat",
            "wget", "curl", "base64", "echo", "export", "env",
        ]
        
        # Check if command looks like it should run on remote system
        should_route_to_ssh = False
        
        # Explicit indicators - flag files
        if any(cmd in command_lower for cmd in ["user.txt", "root.txt", "flag", "proof.txt", "note.txt"]):
            should_route_to_ssh = True
            logger.info(f"Routing to SSH (flag file detected): {command}")
        # File paths that suggest remote system (but not local paths)
        elif any(path in command for path in ["/home/", "/root/", "/tmp/", "/var/", "/opt/", "/usr/local/"]):
            # Exclude local indicators
            if not any(local in command_lower for local in ["localhost", "127.0.0.1", "local", "~/.", "$HOME", "./"]):
                should_route_to_ssh = True
                logger.info(f"Routing to SSH (remote path detected): {command}")
        # Commands that are typically run on remote systems
        elif command_lower.split() and command_lower.split()[0] in ssh_commands:
            # But not if it's clearly a local command
            if not any(local in command_lower for local in ["localhost", "127.0.0.1", "local", "~/.", "$HOME", "./", "nmap", "gobuster"]):
                should_route_to_ssh = True
                logger.info(f"Routing to SSH (system command detected): {command}")
        # If command doesn't look like a local tool (nmap, gobuster, etc.), route to SSH
        elif not any(tool in command_lower.split()[0] if command_lower.split() else False for tool in ["nmap", "gobuster", "dirsearch", "ffuf", "hydra", "enum4linux", "kerbrute"]):
            # Default: if we have an active SSH session and command doesn't look local, route to SSH
            should_route_to_ssh = True
            logger.info(f"Routing to SSH (default for active session): {command}")
        
        if should_route_to_ssh:
            logger.info(f"Routing command to SSH terminal: {ssh_terminal}")
            return ssh_terminal

    return None


def extract_commands_from_response(response: str) -> List[Dict[str, str]]:
    """
    Extract commands from AI response
    Returns list of dicts with 'type' and 'command' keys
    """
    commands = []

    # Extract code blocks
    code_block_pattern = r"```(?:bash|sh|shell)?\n(.*?)```"
    matches = re.findall(code_block_pattern, response, re.DOTALL)

    for match in matches:
        lines = [line.strip() for line in match.strip().split("\n") if line.strip()]
        for line in lines:
            # Skip comments
            if line.startswith("#"):
                continue

            # Check for special directives
            if line.startswith("NEW_TERMINAL:"):
                cmd = line.replace("NEW_TERMINAL:", "").strip()
                commands.append({"type": "new_terminal", "command": cmd})
            elif line.startswith("SPLIT_TERMINAL:"):
                cmd = line.replace("SPLIT_TERMINAL:", "").strip()
                commands.append({"type": "split_terminal", "command": cmd})
            elif line.startswith("SEND_TO_TERMINAL:"):
                # Format: SEND_TO_TERMINAL:terminal_id:command
                parts = line.replace("SEND_TO_TERMINAL:", "").split(":", 1)
                if len(parts) == 2:
                    terminal_id, cmd = parts
                    commands.append(
                        {
                            "type": "send_to_terminal",
                            "terminal_id": terminal_id.strip(),
                            "command": cmd.strip(),
                        }
                    )
            else:
                commands.append({"type": "execute", "command": line})

    # Also look for single line commands
    if not commands:
        # Try to find commands after common prefixes
        lines = response.split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("```"):
                # Check if it looks like a command
                if any(line.startswith(prefix) for prefix in ["$", ">", "%"]):
                    cmd = line.lstrip("$>% ").strip()
                    if cmd:
                        commands.append({"type": "execute", "command": cmd})

    logger.debug(f"Extracted {len(commands)} commands from response")
    return commands


def ask_ai_for_next_steps(
    api_key: str, command_history: List[Dict[str, Any]], max_iterations: int = 5
) -> List[Dict[str, str]]:
    """
    Intelligently analyze results and suggest next steps
    Returns list of commands to execute next
    """
    if not command_history:
        return []

    if OpenAI is None:
        logger.error("OpenAI package not available")
        return []

    # Get recent results
    recent_results = []
    for entry in command_history[-5:]:  # Last 5 commands
        if entry.get("type") == "execute":
            recent_results.append(
                {
                    "command": entry.get("command", ""),
                    "exit_code": entry.get("exit_code", 0),
                    "output": entry.get("output", "")[:2000],  # Limit output size
                }
            )

    if not recent_results:
        return []

    system_info = get_system_info()
    available_tools = get_available_tools()
    available_wordlists = get_available_wordlists_info()

    results_summary = "\n".join(
        [
            f"Command: {r['command']}\nExit Code: {r['exit_code']}\nOutput:\n{r['output']}\n---"
            for r in recent_results
        ]
    )

    system_prompt = f"""You are an intelligent penetration testing assistant. Analyze the results from recent commands and suggest the next logical steps.

System Information:
{system_info}

Available Tools: {available_tools}

Available Wordlists:
{available_wordlists}

RECENT COMMAND RESULTS:
{results_summary}

CRITICAL INSTRUCTIONS:
1. Analyze the results CAREFULLY - look for:
   - Open services/ports that need enumeration
   - Interesting shares, files, or directories discovered
   - Authentication requirements or bypass opportunities
   - Error messages that reveal information
   - Successful access that can be exploited further

2. Suggest ONLY the next logical steps based on findings
3. Be proactive - if you found something interesting (like a Replication share, open ports, etc.), investigate it immediately
4. Format commands in code blocks: ```bash
   command1
   command2
   ```
5. If no more useful steps can be taken, respond with "NO_MORE_STEPS"
6. Prioritize actionable findings - if SMB Replication share is accessible, try to access it
7. If LDAP requires auth, try anonymous bind or other enumeration methods
8. Continue the reconnaissance/enumeration process intelligently

Respond with commands to execute next, or "NO_MORE_STEPS" if the task is complete:"""

    try:
        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": "Based on these results, what should I do next? Continue the reconnaissance and enumeration process.",
                },
            ],
            temperature=0.7,
            max_tokens=1500,
        )

        response_text = response.choices[0].message.content

        if "NO_MORE_STEPS" in response_text.upper() or "no more steps" in response_text.lower():
            return []

        # Extract commands
        commands = extract_commands_from_response(response_text)
        return commands
    except Exception as e:
        logger.error(f"Error getting next steps: {e}")
        return []


def ask_ai_for_commands(
    prompt: str,
    api_key: str,
    context: str = "",
    command_history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Ask AI for commands to execute
    Returns AI response with commands
    """
    if OpenAI is None:
        logger.error("OpenAI package not available")
        return ""

    if command_history is None:
        command_history = []

    system_info = get_system_info()
    available_tools = get_available_tools()
    available_wordlists = get_available_wordlists_info()

    # Build context from command history
    history_context = ""
    failed_commands = []
    active_ssh_session = None
    if command_history:
        history_context = "\n\nPREVIOUS COMMANDS AND OUTPUTS:\n"
        history_context += "=" * 60 + "\n"
        for i, entry in enumerate(command_history[-10:], 1):  # Last 10 commands
            cmd = entry.get("command", "N/A")
            exit_code = entry.get("exit_code", "N/A")
            
            # Check for active SSH session
            if entry.get("ssh_session") and entry.get("controlled"):
                active_ssh_session = {
                    "host": entry.get("ssh_host", "unknown"),
                    "user": entry.get("ssh_user", "unknown"),
                    "terminal_id": entry.get("terminal_id"),
                }
                history_context += f"\nCommand {i}: {cmd} [SSH SESSION ACTIVE - Commands will route here]\n"
            else:
                history_context += f"\nCommand {i}: {cmd}\n"
            
            history_context += f"Exit Code: {exit_code}\n"

            # Track failed commands
            if exit_code != 0 and exit_code != "N/A":
                failed_commands.append((cmd, entry.get("output", "")))

            output = entry.get("output", "")
            if output:
                # Truncate very long outputs
                if len(output) > 3000:
                    output = output[:3000] + "\n... (output truncated)"
                history_context += f"Output:\n{output}\n"
            history_context += "-" * 60 + "\n"
    
    # Add SSH session context if active
    ssh_session_context = ""
    if active_ssh_session:
        ssh_session_context = f"\n\n⚠️ ACTIVE SSH SESSION DETECTED:\n"
        ssh_session_context += f"Connected to: {active_ssh_session['user']}@{active_ssh_session['host']}\n"
        ssh_session_context += f"Terminal ID: {active_ssh_session['terminal_id']}\n"
        ssh_session_context += f"\nIMPORTANT: All subsequent commands (find, cat, ls, grep, etc.) will AUTOMATICALLY be routed to this SSH session.\n"
        ssh_session_context += f"You should use commands as if you're already on the remote system. For example:\n"
        ssh_session_context += f"- Use: find / -name user.txt (NOT: ssh user@host 'find / -name user.txt')\n"
        ssh_session_context += f"- Use: cat /home/user/flag (NOT: ssh user@host 'cat /home/user/flag')\n"
        ssh_session_context += f"- Use: ls -la /home (NOT: ssh user@host 'ls -la /home')\n"
        ssh_session_context += f"The system will automatically send these commands to the SSH session.\n"

    # Analyze previous outputs for key information
    key_findings = ""
    if command_history:
        findings = []
        for entry in command_history[-5:]:  # Last 5 commands
            output = entry.get("output", "").lower()
            # Look for common patterns
            if "port" in output and "open" in output:
                # Extract port numbers
                port_matches = re.findall(r"(\d+)/tcp\s+open", output)
                if port_matches:
                    findings.append(f"Open ports detected: {', '.join(set(port_matches))}")

            if "smb" in output or "445" in output:
                findings.append("SMB service detected on port 445")

            if "ldap" in output or "389" in output:
                findings.append("LDAP service detected on port 389")

            if "kerberos" in output or "88" in output:
                findings.append("Kerberos service detected on port 88")

            if "domain" in output or "active.htb" in output.lower():
                findings.append("Active Directory domain: active.htb")

        if findings:
            key_findings = (
                "\n\nKEY FINDINGS FROM PREVIOUS COMMANDS:\n" + "\n".join(set(findings)) + "\n"
            )

    # Build failed commands context
    failed_context = ""
    if failed_commands:
        failed_context = "\n\nFAILED COMMANDS (DO NOT REPEAT THESE):\n"
        for cmd, output in failed_commands:
            failed_context += f"- {cmd}\n"
            if "command not found" in output.lower():
                tool = cmd.split()[0] if cmd.split() else ""
                failed_context += f"  Reason: Tool '{tool}' not installed\n"
        failed_context += "\nUse alternative tools or built-in commands instead.\n"

    # Extract SSH credentials from prompt if available
    ssh_credentials = extract_ssh_credentials(prompt)
    ssh_context = ""
    if ssh_credentials:
        ssh_context = f"\n\nSSH CREDENTIALS PROVIDED:\n"
        ssh_context += f"User: {ssh_credentials.get('user')}\n"
        ssh_context += f"Host: {ssh_credentials.get('host')}\n"
        ssh_context += f"Password: {'*' * len(ssh_credentials.get('password', ''))}\n"
        ssh_context += f"\nIMPORTANT: When using SSH commands, the system will automatically convert them to use 'sshpass' for non-interactive authentication.\n"
        ssh_context += f"You can use: ssh {ssh_credentials.get('user')}@{ssh_credentials.get('host')} and it will be automatically converted.\n"

    system_prompt = f"""You are an autonomous terminal assistant that executes commands directly. You have full control of the terminal.

System Information:
{system_info}

Available Tools: {available_tools}

Available Wordlists:
{available_wordlists}

{context}

{history_context}

{ssh_session_context}

{key_findings}

{failed_context}

CRITICAL INSTRUCTIONS:
1. You MUST respond with ONLY the commands to execute, one per line
2. Format commands in code blocks: ```bash
   command1
   command2
   ```
3. **MOST IMPORTANT**: Analyze previous command outputs CAREFULLY and use that information to inform your next actions
4. **PARALLEL EXECUTION**: For long-running commands (nmap scans, enumeration, etc.), use NEW_TERMINAL: to run them in parallel
5. **PARALLEL SCANNING**: You can run multiple scans/enumeration tasks in parallel by using NEW_TERMINAL: for each one
6. **PRIORITIZE**: If nmap shows specific ports/services open, prioritize enumeration of those services first
7. If previous command output shows specific results (ports, services, IPs, files, etc.), USE THAT INFORMATION in your next commands
8. **USE AVAILABLE TOOLS**: Only suggest commands using tools that are available. Check the "Available Tools" list above.
9. **USE AVAILABLE WORDLISTS**: Check the "Available Wordlists" list above and use those paths. NEVER use hardcoded paths like /usr/share/wordlists/dirbuster/ - use the actual paths from the list.
10. **ALTERNATIVES**: If a tool failed (command not found), use built-in alternatives:
    - Instead of enum4linux: use smbclient, smbmap, or manual SMB enumeration
    - Instead of kerbrute: use impacket tools or manual Kerberos enumeration
    - Instead of specialized tools: use built-in commands (smbclient, ldapsearch, dig, etc.)
11. **PRIORITIZE BY SERVICE**: If SMB (445) is open, start with SMB enumeration. If LDAP (389) is open, try LDAP enumeration.
12. **FOR LONG-RUNNING COMMANDS**: Always use NEW_TERMINAL: prefix for commands that take a long time (nmap, enumeration, scans, etc.)
13. If you need to open a new terminal window, use: NEW_TERMINAL: command
14. If you need to split terminal, use: SPLIT_TERMINAL: command
15. Be context-aware - extract specific values, ports, IPs, filenames from previous outputs and use them
16. Don't repeat commands that already completed successfully - build on their results
17. **NEVER suggest tools that failed with "command not found" - use alternatives instead**
18. **RUN IN PARALLEL**: When doing reconnaissance, run multiple enumeration tasks in parallel using NEW_TERMINAL:
19. **INTERACTIVE PROGRAMS**: For interactive programs like msfconsole:
    - Use NEW_TERMINAL: msfconsole to open in a controlled terminal
    - After opening, subsequent msfconsole commands (use, set, run, exploit) will automatically be sent to that terminal
    - The AI maintains control over interactive programs in controlled terminals
20. **CONTROLLED TERMINALS**: When a terminal is opened with NEW_TERMINAL:, the AI can send additional commands to it
    - Commands like "use auxiliary/scanner/smb/smb_enumshares" will be sent to existing msfconsole terminals
    - The AI automatically routes commands to the correct controlled terminal
21. **SUBDOMAINS/DOMAINS**: When you discover subdomains or domains (like dc.active.htb), the system will automatically add them to /etc/hosts
    - You don't need to manually add them - just use the domain names in your commands
    - The system tracks discovered domains and their IPs automatically
22. **SSH AUTHENTICATION**: If SSH credentials are provided in the user's request, use regular SSH commands (e.g., ssh user@host)
    - The system will automatically convert them to use 'sshpass' for non-interactive authentication
    - You don't need to manually add sshpass - just use normal SSH commands
23. **SSH SESSIONS - CRITICAL**: When SSH is opened in a controlled terminal, ALL SUBSEQUENT COMMANDS should run on the remote system:
    - After SSH connection is established, commands like "find / -name user.txt", "cat /home/user/flag", "ls -la /home", etc. will AUTOMATICALLY be routed to the SSH session
    - You don't need to prefix commands with "ssh user@host" - just use the commands directly
    - The system automatically detects when commands should run on the remote system vs local
    - If you see "Opened in new controlled terminal" for SSH, that means subsequent commands will go there automatically
    - Commands that look like they should run on remote (file operations, system commands, flag searches) will be sent to the SSH session
    - When looking for flags (user.txt, root.txt), searching files, or running system commands after SSH, just use the commands directly - they'll be routed correctly
{ssh_context}

User's request: {prompt}

Respond with the commands to execute based on the context:"""

    try:
        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=2000,
        )

        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error communicating with OpenAI API: {e}")
        return ""


def execute_commands_sequence(
    commands: List[Dict[str, str]],
    api_key: str,
    command_history: Optional[List[Dict[str, Any]]] = None,
    user_context: str = "",
) -> List[Dict[str, Any]]:
    """Execute a sequence of commands with live output and context awareness"""
    if command_history is None:
        command_history = []

    # Extract SSH credentials from user context (store for use in terminal opening)
    ssh_credentials = extract_ssh_credentials(user_context) if user_context else None
    # Store globally for use in terminal opening
    global global_ssh_credentials
    global_ssh_credentials = ssh_credentials

    print(f"\n{Colors.BOLD}{Colors.BLUE}🤖 Terminal AI is executing commands...{Colors.RESET}\n")

    for i, cmd_info in enumerate(commands, 1):
        cmd_type = cmd_info["type"]
        command = cmd_info["command"]

        if not command:
            continue

        # Safety check
        if is_dangerous_command(command):
            print(
                f"\n{Colors.YELLOW}⚠️  Warning: Potentially dangerous command detected{Colors.RESET}"
            )
            print(f"{Colors.YELLOW}Command: {command}{Colors.RESET}")
            response = (
                input(f"{Colors.YELLOW}Execute anyway? (yes/no): {Colors.RESET}").strip().lower()
            )
            if response != "yes":
                print(f"{Colors.RED}Skipping dangerous command.{Colors.RESET}\n")
                continue

        if cmd_type == "new_terminal":
            print(f"\n{Colors.MAGENTA}🪟 Opening new controlled terminal window...{Colors.RESET}")
            terminal_id = open_new_terminal(command, split=False)
            time.sleep(0.5)
            command_history.append(
                {
                    "command": command,
                    "exit_code": 0,
                    "output": "Opened in new controlled terminal",
                    "type": "new_terminal",
                    "terminal_id": terminal_id,
                    "controlled": True,
                }
            )
            print(
                f"{Colors.GREEN}✓ Terminal ID: {terminal_id} (AI can control this terminal){Colors.RESET}\n"
            )
        elif cmd_type == "split_terminal":
            print(f"\n{Colors.MAGENTA}📑 Splitting terminal...{Colors.RESET}")
            open_new_terminal(command, split=True)
            time.sleep(0.5)
            command_history.append(
                {
                    "command": command,
                    "exit_code": 0,
                    "output": "Opened in split terminal",
                    "type": "split_terminal",
                }
            )
        else:
            # Regular command execution
            # Handle SSH commands specially
            is_ssh_command = re.search(r"^\s*ssh\s+", command, re.IGNORECASE)
            
            if is_ssh_command and ssh_credentials:
                # Try to convert to sshpass
                original_command = command
                command = convert_ssh_to_sshpass(command, ssh_credentials)
                
                if command != original_command:
                    logger.info(f"Converted SSH command: {original_command} -> {command}")
                else:
                    # sshpass not available, but credentials provided
                    # Open in new terminal to avoid hanging
                    print(
                        f"{Colors.YELLOW}⚠️  sshpass not available. Opening SSH in new terminal to avoid password prompt hang...{Colors.RESET}\n"
                    )
                    type_command(original_command)
                    # Pass SSH password to wrapper script
                    ssh_pass = ssh_credentials.get("password") if ssh_credentials else None
                    terminal_id = open_new_terminal(original_command, split=False, ssh_password=ssh_pass)
                    # Extract SSH host info
                    ssh_host = None
                    ssh_user = None
                    if ssh_credentials:
                        ssh_host = ssh_credentials.get("host")
                        ssh_user = ssh_credentials.get("user")
                    else:
                        # Try to extract from command
                        match = re.search(r"ssh\s+([^\s@]+)@([^\s]+)", original_command, re.IGNORECASE)
                        if match:
                            ssh_user = match.group(1)
                            ssh_host = match.group(2)
                    
                    command_history.append(
                        {
                            "command": original_command,
                            "exit_code": 0,
                            "output": "Opened in new controlled terminal (sshpass not available)",
                            "type": "new_terminal",
                            "terminal_id": terminal_id,
                            "controlled": True,
                            "ssh_session": True,
                            "ssh_host": ssh_host,
                            "ssh_user": ssh_user,
                        }
                    )
                    print(
                        f"{Colors.GREEN}✓ Terminal ID: {terminal_id} (AI can control this terminal){Colors.RESET}\n"
                    )
                    continue  # Skip normal execution

            # Check if there are more commands after this one
            remaining_commands = [
                c for c in commands[i:] if c.get("type") == "execute" and c.get("command")
            ]
            has_more_commands = len(remaining_commands) > 0

            # Only open new terminal if:
            # 1. It's a long-running command AND
            # 2. There are more commands to execute
            if is_long_running_command(command) and has_more_commands:
                # Create output file for reading results later
                output_dir = CONFIG_DIR / "terminal_outputs"
                output_dir.mkdir(exist_ok=True)
                output_file = output_dir / f"cmd_{int(time.time())}_{i}.txt"

                print(
                    f"{Colors.CYAN}⏱️  Detected long-running command with more tasks queued. Opening in new controlled terminal for parallel execution...{Colors.RESET}\n"
                )
                type_command(command)
                terminal_id = open_new_terminal(command, split=False, output_file=str(output_file))
                command_history.append(
                    {
                        "command": command,
                        "exit_code": 0,
                        "output": f"Running in new controlled terminal window",
                        "type": "new_terminal",
                        "parallel": True,
                        "output_file": str(output_file),
                        "terminal_id": terminal_id,
                        "controlled": True,
                    }
                )
                print(
                    f"{Colors.GREEN}✓ Terminal ID: {terminal_id} (AI can control this terminal){Colors.RESET}"
                )
                print(
                    f"{Colors.GREEN}✓ Command running in new terminal (parallel execution){Colors.RESET}"
                )
                print(f"{Colors.CYAN}   Output will be saved to: {output_file}{Colors.RESET}\n")
                time.sleep(0.3)  # Small delay to allow terminal to open
            elif is_long_running_command(command) and not has_more_commands:
                # Long-running but no more commands - execute normally with timeout
                timeout = 180  # 3 minutes for long-running commands
                print(
                    f"{Colors.CYAN}⏱️  Detected long-running command. Will continue after {timeout}s if needed...{Colors.RESET}\n"
                )

                # Check if command exists
                exists, tool_name = check_command_exists(command)
                if not exists and tool_name:
                    print(
                        f"{Colors.YELLOW}⚠️  Warning: Tool '{tool_name}' may not be available{Colors.RESET}"
                    )
                    print(f"{Colors.YELLOW}Attempting to execute anyway...{Colors.RESET}\n")

                exit_code, output = execute_command_live(
                    command,
                    timeout=timeout,
                    capture_output=True,
                    api_key=api_key,
                    user_context=user_context,
                    command_history=command_history,
                    use_interactive=True,
                )

                # Check for "command not found" errors
                if exit_code == 127 or (
                    "command not found" in output.lower() or "/bin/sh:" in output.lower()
                ):
                    suggestion = suggest_alternative(command, output)
                    if suggestion:
                        print(f"{Colors.CYAN}💡 {suggestion}{Colors.RESET}\n")

                # Store in history
                command_history.append(
                    {
                        "command": command,
                        "exit_code": exit_code,
                        "output": output,
                        "type": "execute",
                    }
                )

                if exit_code != 0:
                    print(f"{Colors.YELLOW}⚠️  Command exited with code {exit_code}{Colors.RESET}")
                print()  # Extra line for readability
            else:
                # Normal command execution
                # If SSH command without credentials, open in new terminal to avoid hanging
                if is_ssh_command and not ssh_credentials and is_interactive_command(command):
                    print(
                        f"{Colors.YELLOW}⚠️  SSH command detected without credentials. Opening in new terminal to avoid password prompt hang...{Colors.RESET}\n"
                    )
                    type_command(command)
                    # Try to extract password from user context
                    ssh_creds = extract_ssh_credentials(user_context) if user_context else None
                    ssh_pass = ssh_creds.get("password") if ssh_creds else None
                    terminal_id = open_new_terminal(command, split=False, ssh_password=ssh_pass)
                    # Extract SSH host info
                    ssh_host = None
                    ssh_user = None
                    match = re.search(r"ssh\s+([^\s@]+)@([^\s]+)", command, re.IGNORECASE)
                    if match:
                        ssh_user = match.group(1)
                        ssh_host = match.group(2)
                    
                    command_history.append(
                        {
                            "command": command,
                            "exit_code": 0,
                            "output": "Opened in new controlled terminal (SSH without credentials)",
                            "type": "new_terminal",
                            "terminal_id": terminal_id,
                            "controlled": True,
                            "ssh_session": True,
                            "ssh_host": ssh_host,
                            "ssh_user": ssh_user,
                        }
                    )
                    print(
                        f"{Colors.GREEN}✓ Terminal ID: {terminal_id} (AI can control this terminal){Colors.RESET}\n"
                    )
                    continue  # Skip normal execution
                
                # Check if this command should go to an existing controlled terminal
                existing_terminal_id = find_controlled_terminal_for_command(
                    command, command_history
                )

                if existing_terminal_id:
                    # Check if terminal is still active
                    terminal_status = get_terminal_status(existing_terminal_id)
                    if terminal_status == "not_found" or terminal_status == "error":
                        logger.warning(f"Terminal {existing_terminal_id} not found or has error, will execute locally")
                        # Remove from controlled terminals
                        if existing_terminal_id in controlled_terminals:
                            del controlled_terminals[existing_terminal_id]
                        # Fall through to normal execution
                    else:
                        # Send command to existing controlled terminal
                        print(
                            f"{Colors.CYAN}📤 Sending command to controlled terminal ({existing_terminal_id})...{Colors.RESET}\n"
                        )
                        type_command(command)
                        if send_command_to_terminal(existing_terminal_id, command):
                            print(f"{Colors.GREEN}✓ Command sent to terminal{Colors.RESET}")
                            
                            # Wait a bit for command to execute, then read output with timeout
                            time.sleep(2)  # Give command time to start
                            
                            # Try to read output with timeout (shorter timeout to prevent hanging)
                            max_wait_time = 10  # Maximum 10 seconds to wait for output
                            wait_interval = 1   # Check every 1 second
                            output = ""
                            waited = 0
                            
                            while waited < max_wait_time:
                                output = read_terminal_output(existing_terminal_id)
                                
                                # Check if we got meaningful output (not just logs)
                                if output and len(output.strip()) > 20:
                                    output_lower = output.lower()
                                    # Check if output contains actual command results
                                    if any(indicator in output_lower for indicator in [
                                        "executing:", "command completed", "exit code", 
                                        "spawning ssh", "connected successfully",
                                        "\n", "error", "failed", "password"
                                    ]):
                                        # Got some output, break
                                        break
                                
                                # Check terminal status file for errors
                                if existing_terminal_id in controlled_terminals:
                                    control_files = controlled_terminals[existing_terminal_id]["control_files"]
                                    status_file = control_files["status_file"]
                                    if status_file.exists():
                                        status = status_file.read_text().strip()
                                        if "error" in status.lower() or "failed" in status.lower():
                                            logger.warning(f"Terminal {existing_terminal_id} has errors")
                                            output = f"[Terminal error: {status}]"
                                            break
                                
                                time.sleep(wait_interval)
                                waited += wait_interval
                                if waited % 3 == 0:  # Show progress every 3 seconds
                                    print(f"{Colors.YELLOW}⏳ Waiting for terminal output... ({waited}s/{max_wait_time}s){Colors.RESET}")
                            
                            # If we still don't have meaningful output, assume terminal is stuck
                            if not output or len(output.strip()) < 20:
                                logger.warning(f"Terminal {existing_terminal_id} not responding after {waited}s")
                                print(f"{Colors.YELLOW}⚠️  Terminal not responding, executing command locally instead...{Colors.RESET}\n")
                                # Remove from controlled and execute locally
                                if existing_terminal_id in controlled_terminals:
                                    del controlled_terminals[existing_terminal_id]
                                # Fall through to normal execution
                                existing_terminal_id = None
                            
                            if existing_terminal_id:  # Still valid
                                command_history.append(
                                    {
                                        "command": command,
                                        "exit_code": 0,
                                        "output": output,
                                        "type": "execute",
                                        "sent_to_terminal": existing_terminal_id,
                                    }
                                )
                                if output:
                                    print(f"{Colors.CYAN}Output from terminal:{Colors.RESET}")
                                    print(output[-1000:] if len(output) > 1000 else output)
                                print()
                                continue
                        else:
                            logger.warning(f"Failed to send command to terminal {existing_terminal_id}, executing locally")
                            # Remove from controlled terminals
                            if existing_terminal_id in controlled_terminals:
                                del controlled_terminals[existing_terminal_id]
                            # Fall through to normal execution

                # Check if it's an interactive command first
                if is_interactive_command(command):
                    print(f"{Colors.YELLOW}⚠️  Detected interactive program{Colors.RESET}")
                    suggestion = suggest_non_interactive_alternative(command)
                    print(f"{Colors.CYAN}💡 {suggestion}{Colors.RESET}")
                    print(
                        f"{Colors.MAGENTA}🪟 Opening in new controlled terminal...{Colors.RESET}\n"
                    )

                    # Open in new controlled terminal
                    type_command(command)
                    terminal_id = open_new_terminal(command, split=False)
                    command_history.append(
                        {
                            "command": command,
                            "exit_code": 0,
                            "output": "Opened in new controlled terminal (interactive program)",
                            "type": "new_terminal",
                            "interactive": True,
                            "terminal_id": terminal_id,
                            "controlled": True,
                        }
                    )
                    print(
                        f"{Colors.GREEN}✓ Interactive program opened in controlled terminal (ID: {terminal_id}){Colors.RESET}"
                    )
                    print(f"{Colors.CYAN}   AI can send commands to this terminal{Colors.RESET}\n")
                    time.sleep(0.3)
                    continue

                timeout = 60  # Default 1 minute

                # Check if command exists before executing
                exists, tool_name = check_command_exists(command)
                if not exists and tool_name:
                    print(
                        f"{Colors.YELLOW}⚠️  Warning: Tool '{tool_name}' may not be available{Colors.RESET}"
                    )
                    print(f"{Colors.YELLOW}Attempting to execute anyway...{Colors.RESET}\n")

                exit_code, output = execute_command_live(
                    command,
                    timeout=timeout,
                    capture_output=True,
                    api_key=api_key,
                    user_context=user_context,
                    command_history=command_history,
                    use_interactive=True,
                )

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

                # Check for "command not found" errors and suggest alternatives
                if exit_code == 127 or (
                    "command not found" in output.lower() or "/bin/sh:" in output.lower()
                ):
                    suggestion = suggest_alternative(command, output)
                    if suggestion:
                        print(f"{Colors.CYAN}💡 {suggestion}{Colors.RESET}\n")

                # Store in history
                command_history.append(
                    {
                        "command": command,
                        "exit_code": exit_code,
                        "output": output,
                        "type": "execute",
                        "subdomains_found": subdomains,
                    }
                )

                if exit_code != 0:
                    print(f"{Colors.YELLOW}⚠️  Command exited with code {exit_code}{Colors.RESET}")
                print()  # Extra line for readability

    return command_history
