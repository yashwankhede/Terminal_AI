#!/usr/bin/env python3
"""
Terminal AI - An AI-powered terminal assistant
Capable of executing terminal commands and performing system tasks
"""

import os
import sys
import json
import subprocess
import argparse
import time
import re
from pathlib import Path
from typing import Optional, Dict, Any, List

# Try to import readline for command history
try:
    import readline
    READLINE_AVAILABLE = True
except ImportError:
    READLINE_AVAILABLE = False

# Check for required dependencies
try:
    import openai
    from openai import OpenAI
except ImportError:
    print("Error: OpenAI package is not installed.")
    print("Please install it using:")
    print("  pip3 install --user openai")
    print("  or")
    print("  pip3 install --user --break-system-packages openai")
    print("\nOr run the installation script: ./install.sh")
    sys.exit(1)

# Configuration file path
CONFIG_DIR = Path.home() / ".terminal_ai"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Colors for terminal output
class Colors:
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    CYAN = '\033[0;36m'
    MAGENTA = '\033[0;35m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def load_config() -> Dict[str, Any]:
    """Load configuration from file"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to file"""
    CONFIG_DIR.mkdir(exist_ok=True)
    # Set secure permissions (read/write for owner only)
    os.umask(0o077)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    os.chmod(CONFIG_FILE, 0o600)

def get_api_key() -> Optional[str]:
    """Get OpenAI API key from config"""
    config = load_config()
    return config.get('api_key')

def set_api_key(api_key: str) -> None:
    """Set OpenAI API key in config"""
    config = load_config()
    config['api_key'] = api_key
    save_config(config)

def type_command(command: str, speed: float = 0.02):
    """Animate typing a command"""
    print(f"{Colors.CYAN}${Colors.RESET} ", end='', flush=True)
    for char in command:
        print(char, end='', flush=True)
        time.sleep(speed)
    print()  # New line after command

def is_long_running_command(command: str) -> bool:
    """Detect if a command is likely to run for a long time"""
    long_running_patterns = [
        r'\bnmap\b',  # Any nmap command
        r'\bmasscan\b',
        r'\brustscan\b',
        r'\benum4linux\b',
        r'\bkerbrute\b',
        r'\bhydra\b',
        r'\bmedusa\b',
        r'\bgobuster\b',
        r'\bdirb\b',
        r'\bdirsearch\b',
        r'\bffuf\b',
        r'\bnikto\b',
        r'\bsqlmap\b',
        r'\bping\b.*-t',
        r'\btail\s+-f',
        r'\bwatch\b',
        r'\btop\b',
        r'\bhtop\b',
        r'\bwhile\s+true',
        r'>\s+/dev/tty',
        r'\bscan\b',  # Any scan command
        r'\benum\b',  # Any enumeration
    ]
    
    command_lower = command.lower().strip()
    for pattern in long_running_patterns:
        if re.search(pattern, command_lower):
            return True
    return False

def should_run_in_background(command: str) -> bool:
    """Determine if a command should run in background"""
    # Commands that should run in background
    background_patterns = [
        r'\bnmap\s+-p-',  # Full port scans
        r'\bnohup\b',
        r'\b&\s*$',  # Already has & at end
    ]
    
    command_lower = command.lower().strip()
    for pattern in background_patterns:
        if re.search(pattern, command_lower):
            return True
    return False

def is_interactive_command(command: str) -> bool:
    """Detect if a command is interactive (requires user input)"""
    command_lower = command.lower().strip()
    
    # Always interactive programs (even with some flags)
    always_interactive = [
        r'\bmsfconsole\b',  # msfconsole is always interactive unless -x is used
        r'\bpython\s*$',  # python without -c or script
        r'^\s*python3\s*$',
        r'^\s*ruby\s*$',
        r'^\s*irb\s*$',
        r'^\s*bash\s*$',  # bash without -c
        r'^\s*sh\s*$',
        r'^\s*zsh\s*$',
        r'^\s*fish\s*$',
    ]
    
    # Check for always interactive programs first
    for pattern in always_interactive:
        if re.search(pattern, command_lower):
            # msfconsole with -x flag is non-interactive
            if 'msfconsole' in command_lower and '-x' in command_lower:
                return False
            return True
    
    # Conditionally interactive programs
    conditionally_interactive = [
        r'^\s*mysql\s*$',  # mysql without -e or script
        r'^\s*psql\s*$',  # psql without -c or -f
        r'^\s*sqlite3\s+[^-]',  # sqlite3 without -cmd
        r'^\s*nc\s+[^-]',  # netcat in listen mode
        r'^\s*netcat\s+[^-]',
    ]
    
    command_stripped = command.strip()
    for pattern in conditionally_interactive:
        if re.search(pattern, command_stripped, re.IGNORECASE):
            return True
    
    # Check for non-interactive flags that make it non-interactive
    # Note: -q for msfconsole doesn't make it non-interactive, only -x does
    non_interactive_flags = ['-x', '-c', '-e', '-f', '-r', '--execute', '--file', '--resource']
    for flag in non_interactive_flags:
        if flag in command_lower:
            return False  # Has non-interactive flag
    
    return False

def suggest_non_interactive_alternative(command: str) -> str:
    """Suggest non-interactive alternative for interactive commands"""
    command_lower = command.lower().strip()
    
    if 'msfconsole' in command_lower:
        return "Use: msfconsole -q -x 'use exploit/...; set RHOSTS ...; exploit' or open in new terminal"
    elif 'mysql' in command_lower:
        return "Use: mysql -e 'SELECT ...' or mysql < script.sql"
    elif 'psql' in command_lower:
        return "Use: psql -c 'SELECT ...' or psql -f script.sql"
    elif 'python' in command_lower or 'python3' in command_lower:
        return "Use: python -c 'code' or python script.py"
    elif 'bash' in command_lower or 'sh' in command_lower:
        return "Use: bash -c 'command' or bash script.sh"
    
    return "This is an interactive program. Consider using non-interactive flags or opening in a new terminal."

def execute_command_live(command: str, shell: bool = True, show_command: bool = True, timeout: int = 300, capture_output: bool = True) -> tuple[int, str]:
    """
    Execute a terminal command with live output streaming
    Returns: (exit_code, output)
    """
    if show_command:
        type_command(command)
    
    output_lines = []
    last_output_time = None
    prompt_count = 0
    
    try:
        # Use Popen for real-time output
        process = subprocess.Popen(
            command,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Stream output in real-time
        start_time = time.time()
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output, end='', flush=True)
                if capture_output:
                    output_lines.append(output)
                last_output_time = time.time()
                
                # Detect interactive prompts (like msf6 >, mysql>, etc.)
                if re.search(r'(msf\d+\s*>|mysql>\s*|psql>\s*|>>>\s*|In \[\d+\]:\s*)$', output.strip()):
                    prompt_count += 1
                    # If we see multiple prompts with no other output, likely waiting for input
                    if prompt_count >= 3:
                        print(f"\n{Colors.YELLOW}⚠️  Detected interactive prompt. Command appears to be waiting for input.{Colors.RESET}")
                        print(f"{Colors.YELLOW}Terminating and opening in new terminal instead...{Colors.RESET}")
                        process.terminate()
                        return (130, ''.join(output_lines))
            
            # Check for no output for too long (might be waiting for input)
            if last_output_time and (time.time() - last_output_time > 10) and process.poll() is None:
                # Check if process is still running but producing no output
                if is_interactive_command(command):
                    print(f"\n{Colors.YELLOW}⚠️  No output for 10s. Command may be waiting for input.{Colors.RESET}")
                    print(f"{Colors.YELLOW}Terminating and opening in new terminal instead...{Colors.RESET}")
                    process.terminate()
                    return (130, ''.join(output_lines))
            
            # Check timeout
            if time.time() - start_time > timeout:
                print(f"\n{Colors.YELLOW}⚠️  Command timeout after {timeout}s. Continuing...{Colors.RESET}")
                process.terminate()
                break
        
        return_code = process.poll()
        return (return_code if return_code is not None else 0, ''.join(output_lines))
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Command interrupted by user{Colors.RESET}")
        try:
            process.terminate()
        except:
            pass
        return (130, ''.join(output_lines))
    except Exception as e:
        error_msg = f"Error executing command: {str(e)}"
        print(f"{Colors.RED}{error_msg}{Colors.RESET}")
        return (1, error_msg)

def execute_command_safe(command: str, shell: bool = True) -> tuple[str, int]:
    """
    Execute a terminal command safely (for quick checks)
    Returns: (output, exit_code)
    """
    try:
        result = subprocess.run(
            command,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=30
        )
        output = result.stdout + result.stderr
        return output, result.returncode
    except subprocess.TimeoutExpired:
        return "Command timed out", 1
    except Exception as e:
        return f"Error: {str(e)}", 1

# Global dictionary to track controlled terminals
controlled_terminals = {}

def create_terminal_control_system(terminal_id: str) -> Dict[str, Path]:
    """Create control files for a terminal session"""
    control_dir = CONFIG_DIR / "terminal_controls"
    control_dir.mkdir(exist_ok=True)
    
    control_files = {
        'command_file': control_dir / f"{terminal_id}_commands.txt",
        'output_file': control_dir / f"{terminal_id}_output.txt",
        'status_file': control_dir / f"{terminal_id}_status.txt",
        'pid_file': control_dir / f"{terminal_id}_pid.txt"
    }
    
    # Initialize files
    for file_path in control_files.values():
        if file_path.exists():
            file_path.unlink()
        file_path.touch()
    
    return control_files

def get_terminal_wrapper_script(control_files: Dict[str, Path], initial_command: str = None) -> str:
    """Generate a wrapper script that reads commands from control file"""
    cmd_file = control_files['command_file']
    out_file = control_files['output_file']
    status_file = control_files['status_file']
    
    # Escape paths for bash
    cmd_file_str = str(cmd_file).replace("'", "'\\''")
    out_file_str = str(out_file).replace("'", "'\\''")
    status_file_str = str(status_file).replace("'", "'\\''")
    
    # Escape initial command for bash
    if initial_command:
        # Escape single quotes and other special chars
        escaped_init_cmd = initial_command.replace("'", "'\\''")
        init_cmd_part = f'execute_command "{escaped_init_cmd}"'
    else:
        init_cmd_part = ""
    
    wrapper = f'''#!/bin/bash
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
'''
    return wrapper

def open_new_terminal(command: str = None, split: bool = False, output_file: str = None, terminal_id: str = None) -> str:
    """
    Open a new terminal window with AI control capability
    Returns terminal_id for future control
    """
    if terminal_id is None:
        terminal_id = f"term_{int(time.time())}_{os.getpid()}"
    
    # Create control system
    control_files = create_terminal_control_system(terminal_id)
    
    # Generate wrapper script
    wrapper_script = get_terminal_wrapper_script(control_files, command)
    wrapper_file = control_files['command_file'].parent / f"{terminal_id}_wrapper.sh"
    
    with open(wrapper_file, 'w') as f:
        f.write(wrapper_script)
    os.chmod(wrapper_file, 0o755)
    
    # Command to run in new terminal
    if command:
        # Use wrapper script
        terminal_command = f"bash {wrapper_file}"
    else:
        terminal_command = f"bash {wrapper_file}"
    
    if sys.platform == "darwin":
        # macOS - try to detect terminal app
        terminal_app = os.getenv('TERM_PROGRAM', 'Terminal')
        
        # Escape command for AppleScript
        escaped_cmd = terminal_command.replace('\\', '\\\\').replace('"', '\\"')
        
        if terminal_app == 'iTerm.app' or 'iTerm' in terminal_app:
            # iTerm2 - get window ID
            script = f'''
            tell application "iTerm"
                set newWindow to (create window with default profile)
                set windowId to id of newWindow
                tell current session of newWindow
                    write text "{escaped_cmd}"
                end tell
                return windowId
            end tell
            '''
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
            window_id = result.stdout.strip()
        else:
            # Terminal.app - get window ID
            script = f'''
            tell application "Terminal"
                set newTab to (do script "{escaped_cmd}")
                set windowId to id of window 1 whose selected tab is newTab
                activate
                return windowId as string
            end tell
            '''
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
            window_id = result.stdout.strip()
        
        # Store terminal info
        controlled_terminals[terminal_id] = {
            'window_id': window_id,
            'control_files': control_files,
            'wrapper_file': wrapper_file,
            'status': 'active'
        }
        
    elif sys.platform.startswith("linux"):
        # Linux - use tmux or screen for control
        terminals = ['gnome-terminal', 'konsole', 'xterm', 'terminator']
        for term in terminals:
            if subprocess.run(['which', term], capture_output=True).returncode == 0:
                subprocess.Popen([term, '-e', 'bash', '-c', terminal_command + '; exec bash'])
                break
        
        controlled_terminals[terminal_id] = {
            'control_files': control_files,
            'wrapper_file': wrapper_file,
            'status': 'active'
        }
    
    return terminal_id

def send_command_to_terminal(terminal_id: str, command: str) -> bool:
    """Send a command to a controlled terminal"""
    if terminal_id not in controlled_terminals:
        return False
    
    control_files = controlled_terminals[terminal_id]['control_files']
    command_file = control_files['command_file']
    
    try:
        with open(command_file, 'a') as f:
            f.write(command + '\n')
        return True
    except:
        return False

def read_terminal_output(terminal_id: str) -> str:
    """Read output from a controlled terminal"""
    if terminal_id not in controlled_terminals:
        return ""
    
    control_files = controlled_terminals[terminal_id]['control_files']
    output_file = control_files['output_file']
    
    try:
        if output_file.exists():
            with open(output_file, 'r') as f:
                return f.read()
    except:
        pass
    
    return ""

def get_terminal_status(terminal_id: str) -> str:
    """Get status of a controlled terminal"""
    if terminal_id not in controlled_terminals:
        return "not_found"
    
    control_files = controlled_terminals[terminal_id]['control_files']
    status_file = control_files['status_file']
    
    try:
        if status_file.exists():
            with open(status_file, 'r') as f:
                return f.read().strip()
    except:
        pass
    
    return "unknown"

def read_terminal_output_file(output_file: str, timeout: int = 5) -> str:
    """Read output from a terminal output file (legacy function)"""
    if not os.path.exists(output_file):
        return ""
    
    try:
        with open(output_file, 'r') as f:
            return f.read()
    except:
        return ""

def check_parallel_outputs(command_history: List[Dict[str, Any]]) -> None:
    """Check and update command history with output from parallel terminals"""
    for entry in command_history:
        # Check for new terminal control system
        if entry.get('terminal_id'):
            terminal_id = entry.get('terminal_id')
            output = read_terminal_output(terminal_id)
            if output and output != entry.get('output', ''):
                entry['output'] = output
                # Try to detect if command completed
                if 'Nmap done' in output or 'completed' in output.lower() or 'finished' in output.lower():
                    entry['exit_code'] = 0
                    entry['completed'] = True
        # Legacy support for output_file
        elif entry.get('parallel') and entry.get('output_file'):
            output_file = entry.get('output_file')
            if os.path.exists(output_file):
                # Read the output
                output = read_terminal_output_file(output_file)
                if output and output != entry.get('output', ''):
                    # Update the entry with new output
                    entry['output'] = output
                    # Try to detect if command completed
                    if 'Nmap done' in output or 'completed' in output.lower() or 'finished' in output.lower():
                        entry['exit_code'] = 0
                        entry['completed'] = True

def get_system_info() -> str:
    """Get system information for context"""
    info = []
    
    # OS info
    if sys.platform == "darwin":
        info.append(f"OS: macOS")
        try:
            result = subprocess.run(['sw_vers'], capture_output=True, text=True)
            info.append(result.stdout.strip())
        except:
            pass
    elif sys.platform.startswith("linux"):
        info.append(f"OS: Linux")
        try:
            result = subprocess.run(['uname', '-a'], capture_output=True, text=True)
            info.append(result.stdout.strip())
        except:
            pass
    
    # Current directory
    info.append(f"Current directory: {os.getcwd()}")
    
    # User info
    info.append(f"User: {os.getenv('USER', 'unknown')}")
    
    # Shell
    info.append(f"Shell: {os.getenv('SHELL', 'unknown')}")
    
    return "\n".join(info)

def is_dangerous_command(command: str) -> bool:
    """Check if a command is potentially dangerous"""
    dangerous_patterns = [
        r'\brm\s+-rf\s+/',
        r'\bdd\s+if=',
        r'\bformat\s+',
        r'\bmkfs\s+',
        r'>\s+/dev/sd',
        r'\bsudo\s+rm\s+-rf',
    ]
    
    command_lower = command.lower().strip()
    for pattern in dangerous_patterns:
        if re.search(pattern, command_lower):
            return True
    return False

def check_command_exists(command: str) -> tuple[bool, str]:
    """
    Check if a command/tool exists in the system
    Returns: (exists, tool_name)
    """
    # Extract the first word (command name) from the command string
    # Handle pipes, redirects, etc.
    parts = command.strip().split()
    if not parts:
        return False, ""
    
    # Get the base command (first word, excluding special chars)
    base_cmd = parts[0]
    
    # Remove any special characters and path separators
    base_cmd = re.sub(r'[;&|<>/]', '', base_cmd)
    
    if not base_cmd:
        return False, ""
    
    # Check using command -v (POSIX standard)
    try:
        result = subprocess.run(
            ['command', '-v', base_cmd],
            shell=False,
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0 and result.stdout.strip():
            return True, base_cmd
    except:
        pass
    
    # Fallback to which
    try:
        result = subprocess.run(
            ['which', base_cmd],
            shell=False,
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0 and result.stdout.strip():
            return True, base_cmd
    except:
        pass
    
    return False, base_cmd

def find_wordlists() -> Dict[str, str]:
    """Find available wordlists/SecLists in common locations"""
    wordlists = {}
    
    # Common wordlist locations
    common_locations = [
        '/usr/share/wordlists',
        '/usr/share/seclists',
        '/opt/SecLists',
        '~/SecLists',
        '~/wordlists',
        '/usr/share/dirb/wordlists',
        '/usr/share/dirbuster/wordlists',
    ]
    
    # Common wordlist files to look for
    wordlist_patterns = [
        ('directory-list-2.3-medium.txt', 'dirbuster-medium'),
        ('directory-list-2.3-big.txt', 'dirbuster-big'),
        ('directory-list-2.3-small.txt', 'dirbuster-small'),
        ('Discovery/DNS/subdomains-top1million-110000.txt', 'seclists-dns-top1m'),
        ('Discovery/DNS/subdomains-top1million-5000.txt', 'seclists-dns-top5k'),
        ('Discovery/Web-Content/directory-list-2.3-medium.txt', 'seclists-dir-medium'),
        ('Discovery/Web-Content/raft-medium-directories.txt', 'seclists-raft-medium-dirs'),
        ('Discovery/Web-Content/raft-medium-files.txt', 'seclists-raft-medium-files'),
        ('Discovery/Web-Content/big.txt', 'seclists-big'),
        ('Discovery/Web-Content/common.txt', 'seclists-common'),
        ('Passwords/Common-Credentials/10-million-password-list-top-1000000.txt', 'seclists-passwords-top1m'),
        ('Usernames/xato-net-10-million-usernames.txt', 'seclists-usernames-xato'),
    ]
    
    for location in common_locations:
        # Expand ~
        expanded_location = os.path.expanduser(location)
        if os.path.exists(expanded_location):
            for pattern, key in wordlist_patterns:
                full_path = os.path.join(expanded_location, pattern)
                if os.path.exists(full_path):
                    wordlists[key] = full_path
    
    # Also search recursively for common filenames
    for location in common_locations:
        expanded_location = os.path.expanduser(location)
        if os.path.exists(expanded_location):
            for root, dirs, files in os.walk(expanded_location):
                for file in files:
                    if 'directory-list' in file.lower() or 'common.txt' in file.lower() or 'big.txt' in file.lower():
                        full_path = os.path.join(root, file)
                        key = f"wordlist-{os.path.basename(root)}-{file}"
                        if key not in wordlists:
                            wordlists[key] = full_path
    
    return wordlists

def get_available_wordlists_info() -> str:
    """Get formatted string of available wordlists"""
    wordlists = find_wordlists()
    if not wordlists:
        return "No wordlists found"
    
    info = []
    for key, path in sorted(wordlists.items()):
        info.append(f"{key}: {path}")
    
    return "\n".join(info)

def extract_subdomains_and_ips(output: str) -> List[Dict[str, str]]:
    """Extract subdomains and their IPs from command output"""
    results = []
    
    # Pattern to match subdomains/domains with IPs
    # Examples: "dc.active.htb" or "active.htb" with IP "10.129.222.192"
    patterns = [
        # DNS output patterns
        (r'(\S+\.htb|\S+\.local|\S+\.internal)\s+(\d+\.\d+\.\d+\.\d+)', 'dns'),
        (r'(\d+\.\d+\.\d+\.\d+)\s+(\S+\.htb|\S+\.local|\S+\.internal)', 'reverse'),
        # Nmap output
        (r'Nmap scan report for (\S+\.htb|\S+\.local|\S+\.internal)\s+\((\d+\.\d+\.\d+\.\d+)\)', 'nmap'),
        # dig/nslookup output
        (r'(\S+\.htb|\S+\.local|\S+\.internal)\.\s+\d+\s+IN\s+A\s+(\d+\.\d+\.\d+\.\d+)', 'dig'),
        # Generic domain patterns
        (r'(\S+\.(?:htb|local|internal|test|dev))\s+.*?(\d+\.\d+\.\d+\.\d+)', 'generic'),
    ]
    
    for pattern, source in patterns:
        matches = re.finditer(pattern, output, re.IGNORECASE)
        for match in matches:
            if len(match.groups()) >= 2:
                domain = match.group(1).strip()
                ip = match.group(2).strip()
                # Validate IP
                if re.match(r'^\d+\.\d+\.\d+\.\d+$', ip):
                    results.append({
                        'domain': domain,
                        'ip': ip,
                        'source': source
                    })
    
    # Also look for domains mentioned in commands
    command_pattern = r'(\S+\.(?:htb|local|internal|test|dev))'
    domain_matches = re.findall(command_pattern, output, re.IGNORECASE)
    for domain in domain_matches:
        # Try to find associated IP from context
        ip_pattern = rf'{re.escape(domain)}.*?(\d+\.\d+\.\d+\.\d+)'
        ip_match = re.search(ip_pattern, output, re.IGNORECASE)
        if ip_match:
            ip = ip_match.group(1)
            results.append({
                'domain': domain,
                'ip': ip,
                'source': 'context'
            })
    
    return results

def add_to_hosts_file(domain: str, ip: str) -> bool:
    """Add domain to /etc/hosts file"""
    hosts_file = Path('/etc/hosts')
    
    # Check if entry already exists
    try:
        if hosts_file.exists():
            with open(hosts_file, 'r') as f:
                content = f.read()
                if domain in content and ip in content:
                    return True  # Already exists
    except:
        pass
    
    # Add entry (requires sudo)
    entry = f"{ip}\t{domain}\n"
    
    try:
        # Try to add without sudo first (might work if user has write access)
        with open(hosts_file, 'a') as f:
            f.write(entry)
        return True
    except PermissionError:
        # Need sudo
        try:
            result = subprocess.run(
                ['sudo', 'sh', '-c', f'echo "{entry}" >> {hosts_file}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
    except:
        return False

def get_available_tools() -> str:
    """Get list of commonly used security/recon tools that are available"""
    tools = []
    common_tools = [
        'nmap', 'masscan', 'rustscan',
        'enum4linux', 'smbclient', 'smbmap', 'crackmapexec',
        'kerbrute', 'impacket-scripts',
        'ldapsearch', 'ldapdomaindump',
        'dig', 'nslookup', 'host',
        'nikto', 'gobuster', 'dirb', 'dirsearch', 'ffuf',
        'sqlmap', 'hydra', 'medusa',
        'metasploit', 'msfconsole',
        'nuclei', 'gau', 'waybackurls',
    ]
    
    for tool in common_tools:
        exists, _ = check_command_exists(tool)
        if exists:
            tools.append(tool)
    
    return ", ".join(tools) if tools else "None detected"

def suggest_alternative(command: str, output: str) -> str:
    """Suggest alternative commands when a tool is not found"""
    command_lower = command.lower()
    
    # Map missing tools to alternatives
    alternatives = {
        'enum4linux': 'smbclient, smbmap, or crackmapexec',
        'kerbrute': 'impacket-GetNPUsers or manual Kerberos enumeration',
        'crackmapexec': 'smbclient or smbmap',
        'ldapdomaindump': 'ldapsearch with manual parsing',
    }
    
    for tool, alt in alternatives.items():
        if tool in command_lower:
            return f"Alternative: Use {alt} instead"
    
    # Check for "command not found" errors
    if 'command not found' in output.lower() or 'not found' in output.lower():
        tool_name = command.split()[0] if command.split() else ""
        return f"Tool '{tool_name}' not found. Consider installing it or using built-in alternatives."
    
    return ""

def ask_ai_for_next_steps(api_key: str, command_history: List[Dict[str, Any]], max_iterations: int = 5) -> List[Dict[str, str]]:
    """
    Intelligently analyze results and suggest next steps
    Returns list of commands to execute next
    """
    if not command_history:
        return []
    
    # Get recent results
    recent_results = []
    for entry in command_history[-5:]:  # Last 5 commands
        if entry.get('type') == 'execute':
            recent_results.append({
                'command': entry.get('command', ''),
                'exit_code': entry.get('exit_code', 0),
                'output': entry.get('output', '')[:2000]  # Limit output size
            })
    
    if not recent_results:
        return []
    
    system_info = get_system_info()
    available_tools = get_available_tools()
    available_wordlists = get_available_wordlists_info()
    
    results_summary = "\n".join([
        f"Command: {r['command']}\nExit Code: {r['exit_code']}\nOutput:\n{r['output']}\n---"
        for r in recent_results
    ])
    
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
                {"role": "user", "content": "Based on these results, what should I do next? Continue the reconnaissance and enumeration process."}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        response_text = response.choices[0].message.content
        
        if "NO_MORE_STEPS" in response_text.upper() or "no more steps" in response_text.lower():
            return []
        
        # Extract commands
        commands = extract_commands_from_response(response_text)
        return commands
    except Exception as e:
        print(f"{Colors.RED}Error getting next steps: {str(e)}{Colors.RESET}")
        return []

def ask_ai_for_commands(prompt: str, api_key: str, context: str = "", command_history: List[Dict[str, Any]] = None) -> str:
    """
    Ask AI for commands to execute
    Returns AI response with commands
    """
    system_info = get_system_info()
    available_tools = get_available_tools()
    available_wordlists = get_available_wordlists_info()
    
    # Build context from command history
    history_context = ""
    failed_commands = []
    if command_history:
        history_context = "\n\nPREVIOUS COMMANDS AND OUTPUTS:\n"
        history_context += "=" * 60 + "\n"
        for i, entry in enumerate(command_history[-10:], 1):  # Last 10 commands
            cmd = entry.get('command', 'N/A')
            exit_code = entry.get('exit_code', 'N/A')
            history_context += f"\nCommand {i}: {cmd}\n"
            history_context += f"Exit Code: {exit_code}\n"
            
            # Track failed commands
            if exit_code != 0 and exit_code != 'N/A':
                failed_commands.append((cmd, entry.get('output', '')))
            
            output = entry.get('output', '')
            if output:
                # Truncate very long outputs
                if len(output) > 3000:
                    output = output[:3000] + "\n... (output truncated)"
                history_context += f"Output:\n{output}\n"
            history_context += "-" * 60 + "\n"
    
    # Analyze previous outputs for key information
    key_findings = ""
    if command_history:
        findings = []
        for entry in command_history[-5:]:  # Last 5 commands
            output = entry.get('output', '').lower()
            # Look for common patterns
            if 'port' in output and 'open' in output:
                # Extract port numbers
                port_matches = re.findall(r'(\d+)/tcp\s+open', output)
                if port_matches:
                    findings.append(f"Open ports detected: {', '.join(set(port_matches))}")
            
            if 'smb' in output or '445' in output:
                findings.append("SMB service detected on port 445")
            
            if 'ldap' in output or '389' in output:
                findings.append("LDAP service detected on port 389")
            
            if 'kerberos' in output or '88' in output:
                findings.append("Kerberos service detected on port 88")
            
            if 'domain' in output or 'active.htb' in output.lower():
                findings.append("Active Directory domain: active.htb")
        
        if findings:
            key_findings = "\n\nKEY FINDINGS FROM PREVIOUS COMMANDS:\n" + "\n".join(set(findings)) + "\n"
    
    # Build failed commands context
    failed_context = ""
    if failed_commands:
        failed_context = "\n\nFAILED COMMANDS (DO NOT REPEAT THESE):\n"
        for cmd, output in failed_commands:
            failed_context += f"- {cmd}\n"
            if 'command not found' in output.lower():
                tool = cmd.split()[0] if cmd.split() else ""
                failed_context += f"  Reason: Tool '{tool}' not installed\n"
        failed_context += "\nUse alternative tools or built-in commands instead.\n"
    
    system_prompt = f"""You are an autonomous terminal assistant that executes commands directly. You have full control of the terminal.

System Information:
{system_info}

Available Tools: {available_tools}

Available Wordlists:
{available_wordlists}

{context}

{history_context}

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

User's request: {prompt}

Respond with the commands to execute based on the context:"""

    try:
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"{Colors.RED}Error communicating with OpenAI API: {str(e)}{Colors.RESET}")
        return ""

def find_controlled_terminal_for_command(command: str, command_history: List[Dict[str, Any]]) -> Optional[str]:
    """Find an existing controlled terminal that can handle this command"""
    command_lower = command.lower()
    
    # Check if command is for an interactive program that's already running
    if 'msfconsole' in command_lower or 'use ' in command_lower or 'set ' in command_lower or 'run' == command_lower.strip():
        # Look for existing msfconsole terminal
        for entry in reversed(command_history):
            if entry.get('controlled') and entry.get('interactive'):
                if 'msfconsole' in entry.get('command', '').lower():
                    return entry.get('terminal_id')
    
    return None

def extract_commands_from_response(response: str) -> List[Dict[str, str]]:
    """
    Extract commands from AI response
    Returns list of dicts with 'type' and 'command' keys
    """
    commands = []
    
    # Extract code blocks
    code_block_pattern = r'```(?:bash|sh|shell)?\n(.*?)```'
    matches = re.findall(code_block_pattern, response, re.DOTALL)
    
    for match in matches:
        lines = [line.strip() for line in match.strip().split('\n') if line.strip()]
        for line in lines:
            # Skip comments
            if line.startswith('#'):
                continue
            
            # Check for special directives
            if line.startswith('NEW_TERMINAL:'):
                cmd = line.replace('NEW_TERMINAL:', '').strip()
                commands.append({'type': 'new_terminal', 'command': cmd})
            elif line.startswith('SPLIT_TERMINAL:'):
                cmd = line.replace('SPLIT_TERMINAL:', '').strip()
                commands.append({'type': 'split_terminal', 'command': cmd})
            elif line.startswith('SEND_TO_TERMINAL:'):
                # Format: SEND_TO_TERMINAL:terminal_id:command
                parts = line.replace('SEND_TO_TERMINAL:', '').split(':', 1)
                if len(parts) == 2:
                    terminal_id, cmd = parts
                    commands.append({'type': 'send_to_terminal', 'terminal_id': terminal_id.strip(), 'command': cmd.strip()})
            else:
                commands.append({'type': 'execute', 'command': line})
    
    # Also look for single line commands
    if not commands:
        # Try to find commands after common prefixes
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('```'):
                # Check if it looks like a command
                if any(line.startswith(prefix) for prefix in ['$', '>', '%']):
                    cmd = line.lstrip('$>% ').strip()
                    if cmd:
                        commands.append({'type': 'execute', 'command': cmd})
    
    return commands

def execute_commands_sequence(commands: List[Dict[str, str]], api_key: str, command_history: List[Dict[str, Any]] = None):
    """Execute a sequence of commands with live output and context awareness"""
    if command_history is None:
        command_history = []
    
    print(f"\n{Colors.BOLD}{Colors.BLUE}🤖 Terminal AI is executing commands...{Colors.RESET}\n")
    
    for i, cmd_info in enumerate(commands, 1):
        cmd_type = cmd_info['type']
        command = cmd_info['command']
        
        if not command:
            continue
        
        # Safety check
        if is_dangerous_command(command):
            print(f"\n{Colors.YELLOW}⚠️  Warning: Potentially dangerous command detected{Colors.RESET}")
            print(f"{Colors.YELLOW}Command: {command}{Colors.RESET}")
            response = input(f"{Colors.YELLOW}Execute anyway? (yes/no): {Colors.RESET}").strip().lower()
            if response != 'yes':
                print(f"{Colors.RED}Skipping dangerous command.{Colors.RESET}\n")
                continue
        
        if cmd_type == 'new_terminal':
            print(f"\n{Colors.MAGENTA}🪟 Opening new controlled terminal window...{Colors.RESET}")
            terminal_id = open_new_terminal(command, split=False)
            time.sleep(0.5)
            command_history.append({
                'command': command,
                'exit_code': 0,
                'output': 'Opened in new controlled terminal',
                'type': 'new_terminal',
                'terminal_id': terminal_id,
                'controlled': True
            })
            print(f"{Colors.GREEN}✓ Terminal ID: {terminal_id} (AI can control this terminal){Colors.RESET}\n")
        elif cmd_type == 'split_terminal':
            print(f"\n{Colors.MAGENTA}📑 Splitting terminal...{Colors.RESET}")
            open_new_terminal(command, split=True)
            time.sleep(0.5)
            command_history.append({
                'command': command,
                'exit_code': 0,
                'output': 'Opened in split terminal',
                'type': 'split_terminal'
            })
        else:
            # Regular command execution
            # Check if there are more commands after this one
            remaining_commands = [c for c in commands[i:] if c.get('type') == 'execute' and c.get('command')]
            has_more_commands = len(remaining_commands) > 0
            
            # Only open new terminal if:
            # 1. It's a long-running command AND
            # 2. There are more commands to execute
            if is_long_running_command(command) and has_more_commands:
                # Create output file for reading results later
                output_dir = CONFIG_DIR / "terminal_outputs"
                output_dir.mkdir(exist_ok=True)
                output_file = output_dir / f"cmd_{int(time.time())}_{i}.txt"
                
                print(f"{Colors.CYAN}⏱️  Detected long-running command with more tasks queued. Opening in new controlled terminal for parallel execution...{Colors.RESET}\n")
                type_command(command)
                terminal_id = open_new_terminal(command, split=False, output_file=str(output_file))
                command_history.append({
                    'command': command,
                    'exit_code': 0,
                    'output': f'Running in new controlled terminal window',
                    'type': 'new_terminal',
                    'parallel': True,
                    'output_file': str(output_file),
                    'terminal_id': terminal_id,
                    'controlled': True
                })
                print(f"{Colors.GREEN}✓ Terminal ID: {terminal_id} (AI can control this terminal){Colors.RESET}")
                print(f"{Colors.GREEN}✓ Command running in new terminal (parallel execution){Colors.RESET}")
                print(f"{Colors.CYAN}   Output will be saved to: {output_file}{Colors.RESET}\n")
                time.sleep(0.3)  # Small delay to allow terminal to open
            elif is_long_running_command(command) and not has_more_commands:
                # Long-running but no more commands - execute normally with timeout
                timeout = 180  # 3 minutes for long-running commands
                print(f"{Colors.CYAN}⏱️  Detected long-running command. Will continue after {timeout}s if needed...{Colors.RESET}\n")
                
                # Check if command exists
                exists, tool_name = check_command_exists(command)
                if not exists and tool_name:
                    print(f"{Colors.YELLOW}⚠️  Warning: Tool '{tool_name}' may not be available{Colors.RESET}")
                    print(f"{Colors.YELLOW}Attempting to execute anyway...{Colors.RESET}\n")
                
                exit_code, output = execute_command_live(command, timeout=timeout, capture_output=True)
                
                # Check for "command not found" errors
                if exit_code == 127 or ('command not found' in output.lower() or '/bin/sh:' in output.lower()):
                    suggestion = suggest_alternative(command, output)
                    if suggestion:
                        print(f"{Colors.CYAN}💡 {suggestion}{Colors.RESET}\n")
                
                # Store in history
                command_history.append({
                    'command': command,
                    'exit_code': exit_code,
                    'output': output,
                    'type': 'execute'
                })
                
                if exit_code != 0:
                    print(f"{Colors.YELLOW}⚠️  Command exited with code {exit_code}{Colors.RESET}")
                print()  # Extra line for readability
            else:
                # Normal command execution
                # Check if this command should go to an existing controlled terminal
                existing_terminal_id = find_controlled_terminal_for_command(command, command_history)
                
                if existing_terminal_id:
                    # Send command to existing controlled terminal
                    print(f"{Colors.CYAN}📤 Sending command to controlled terminal ({existing_terminal_id})...{Colors.RESET}\n")
                    type_command(command)
                    if send_command_to_terminal(existing_terminal_id, command):
                        print(f"{Colors.GREEN}✓ Command sent to terminal{Colors.RESET}")
                        time.sleep(1)
                        output = read_terminal_output(existing_terminal_id)
                        command_history.append({
                            'command': command,
                            'exit_code': 0,
                            'output': output,
                            'type': 'execute',
                            'sent_to_terminal': existing_terminal_id
                        })
                        if output:
                            print(f"{Colors.CYAN}Output from terminal:{Colors.RESET}")
                            print(output[-500:] if len(output) > 500 else output)
                        print()
                        continue
                
                # Check if it's an interactive command first
                if is_interactive_command(command):
                    print(f"{Colors.YELLOW}⚠️  Detected interactive program{Colors.RESET}")
                    suggestion = suggest_non_interactive_alternative(command)
                    print(f"{Colors.CYAN}💡 {suggestion}{Colors.RESET}")
                    print(f"{Colors.MAGENTA}🪟 Opening in new controlled terminal...{Colors.RESET}\n")
                    
                    # Open in new controlled terminal
                    type_command(command)
                    terminal_id = open_new_terminal(command, split=False)
                    command_history.append({
                        'command': command,
                        'exit_code': 0,
                        'output': 'Opened in new controlled terminal (interactive program)',
                        'type': 'new_terminal',
                        'interactive': True,
                        'terminal_id': terminal_id,
                        'controlled': True
                    })
                    print(f"{Colors.GREEN}✓ Interactive program opened in controlled terminal (ID: {terminal_id}){Colors.RESET}")
                    print(f"{Colors.CYAN}   AI can send commands to this terminal{Colors.RESET}\n")
                    time.sleep(0.3)
                    continue
                
                timeout = 60  # Default 1 minute
                
                # Check if command exists before executing
                exists, tool_name = check_command_exists(command)
                if not exists and tool_name:
                    print(f"{Colors.YELLOW}⚠️  Warning: Tool '{tool_name}' may not be available{Colors.RESET}")
                    print(f"{Colors.YELLOW}Attempting to execute anyway...{Colors.RESET}\n")
                
                exit_code, output = execute_command_live(command, timeout=timeout, capture_output=True)
                
                # Extract subdomains/domains and add to /etc/hosts
                subdomains = extract_subdomains_and_ips(output)
                for subdomain_info in subdomains:
                    domain = subdomain_info['domain']
                    ip = subdomain_info['ip']
                    if add_to_hosts_file(domain, ip):
                        print(f"{Colors.GREEN}✓ Added {domain} -> {ip} to /etc/hosts{Colors.RESET}")
                    else:
                        print(f"{Colors.YELLOW}⚠️  Could not add {domain} to /etc/hosts (may need sudo){Colors.RESET}")
                
                # Check for "command not found" errors and suggest alternatives
                if exit_code == 127 or ('command not found' in output.lower() or '/bin/sh:' in output.lower()):
                    suggestion = suggest_alternative(command, output)
                    if suggestion:
                        print(f"{Colors.CYAN}💡 {suggestion}{Colors.RESET}\n")
                
                # Store in history
                command_history.append({
                    'command': command,
                    'exit_code': exit_code,
                    'output': output,
                    'type': 'execute',
                    'subdomains_found': subdomains
                })
                
                if exit_code != 0:
                    print(f"{Colors.YELLOW}⚠️  Command exited with code {exit_code}{Colors.RESET}")
                print()  # Extra line for readability
    
    return command_history

def interactive_mode(api_key: str):
    """Interactive mode with live command execution and context awareness"""
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
        except:
            pass
    
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
                except:
                    pass
            
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit']:
                print(f"{Colors.CYAN}Goodbye!{Colors.RESET}")
                break
            
            if user_input.lower() == 'help':
                print(f"\n{Colors.BOLD}Commands:{Colors.RESET}")
                print("  exit/quit - Exit the program")
                print("  help - Show this help message")
                print("  execute <command> - Execute a command directly")
                print("  history - Show recent command history")
                print("  clear - Clear command history")
                print("\nOr just describe what you want and I'll do it!\n")
                continue
            
            if user_input.lower() == 'history':
                if command_history:
                    print(f"\n{Colors.BOLD}Recent Command History:{Colors.RESET}\n")
                    for i, entry in enumerate(command_history[-10:], 1):
                        print(f"{i}. {entry.get('command', 'N/A')}")
                        print(f"   Exit Code: {entry.get('exit_code', 'N/A')}")
                        output = entry.get('output', '')
                        if output and len(output) > 100:
                            print(f"   Output: {output[:100]}...")
                        elif output:
                            print(f"   Output: {output}")
                        print()
                else:
                    print(f"{Colors.YELLOW}No command history yet.{Colors.RESET}\n")
                continue
            
            if user_input.lower() == 'clear':
                command_history.clear()
                print(f"{Colors.GREEN}Command history cleared.{Colors.RESET}\n")
                continue
            
            if user_input.startswith('execute '):
                cmd = user_input[8:].strip()
                exit_code, output = execute_command_live(cmd, capture_output=True)
                
                # Extract subdomains/domains and add to /etc/hosts
                subdomains = extract_subdomains_and_ips(output)
                for subdomain_info in subdomains:
                    domain = subdomain_info['domain']
                    ip = subdomain_info['ip']
                    if add_to_hosts_file(domain, ip):
                        print(f"{Colors.GREEN}✓ Added {domain} -> {ip} to /etc/hosts{Colors.RESET}")
                    else:
                        print(f"{Colors.YELLOW}⚠️  Could not add {domain} to /etc/hosts (may need sudo){Colors.RESET}")
                
                command_history.append({
                    'command': cmd,
                    'exit_code': exit_code,
                    'output': output,
                    'type': 'execute',
                    'subdomains_found': subdomains
                })
                print()
                continue
            
            # Get commands from AI with context
            print(f"\n{Colors.BLUE}🤔 Processing your request (with context from {len(command_history)} previous commands)...{Colors.RESET}\n")
            response = ask_ai_for_commands(user_input, api_key, command_history=command_history)
            
            if not response:
                print(f"{Colors.RED}No response from AI.{Colors.RESET}\n")
                continue
            
            # Extract commands
            commands = extract_commands_from_response(response)
            
            if commands:
                # Execute commands iteratively - one at a time, getting context for next
                for cmd_info in commands:
                    cmd_type = cmd_info['type']
                    command = cmd_info['command']
                    
                    if not command:
                        continue
                    
                    # Safety check
                    if is_dangerous_command(command):
                        print(f"\n{Colors.YELLOW}⚠️  Warning: Potentially dangerous command detected{Colors.RESET}")
                        print(f"{Colors.YELLOW}Command: {command}{Colors.RESET}")
                        response = input(f"{Colors.YELLOW}Execute anyway? (yes/no): {Colors.RESET}").strip().lower()
                        if response != 'yes':
                            print(f"{Colors.RED}Skipping dangerous command.{Colors.RESET}\n")
                            continue
                    
                    if cmd_type == 'new_terminal':
                        print(f"\n{Colors.MAGENTA}🪟 Opening new controlled terminal window...{Colors.RESET}")
                        terminal_id = open_new_terminal(command, split=False)
                        time.sleep(0.5)
                        command_history.append({
                            'command': command,
                            'exit_code': 0,
                            'output': 'Opened in new controlled terminal',
                            'type': 'new_terminal',
                            'terminal_id': terminal_id,
                            'controlled': True
                        })
                        print(f"{Colors.GREEN}✓ Terminal ID: {terminal_id} (AI can control this terminal){Colors.RESET}\n")
                    elif cmd_type == 'split_terminal':
                        print(f"\n{Colors.MAGENTA}📑 Splitting terminal...{Colors.RESET}")
                        open_new_terminal(command, split=True)
                        time.sleep(0.5)
                        command_history.append({
                            'command': command,
                            'exit_code': 0,
                            'output': 'Opened in split terminal',
                            'type': 'split_terminal'
                        })
                    else:
                        # Check if this command should go to an existing controlled terminal
                        existing_terminal_id = find_controlled_terminal_for_command(command, command_history)
                        
                        if existing_terminal_id:
                            # Send command to existing controlled terminal
                            print(f"{Colors.CYAN}📤 Sending command to controlled terminal ({existing_terminal_id})...{Colors.RESET}\n")
                            type_command(command)
                            if send_command_to_terminal(existing_terminal_id, command):
                                print(f"{Colors.GREEN}✓ Command sent to terminal{Colors.RESET}")
                                # Read output after a short delay
                                time.sleep(1)
                                output = read_terminal_output(existing_terminal_id)
                                command_history.append({
                                    'command': command,
                                    'exit_code': 0,
                                    'output': output,
                                    'type': 'execute',
                                    'sent_to_terminal': existing_terminal_id
                                })
                                if output:
                                    print(f"{Colors.CYAN}Output from terminal:{Colors.RESET}")
                                    print(output[-500:] if len(output) > 500 else output)  # Show last 500 chars
                                print()
                                continue
                            else:
                                print(f"{Colors.RED}Failed to send command to terminal{Colors.RESET}\n")
                        
                        # Execute command and get output
                        # Check if there are more commands after this one
                        cmd_index = commands.index(cmd_info)
                        remaining_commands = [c for c in commands[cmd_index+1:] if c.get('type') == 'execute' and c.get('command')]
                        has_more_commands = len(remaining_commands) > 0
                        
                        # Only open new terminal if it's long-running AND there are more commands
                        if is_long_running_command(command) and has_more_commands:
                            # Create output file for reading results later
                            output_dir = CONFIG_DIR / "terminal_outputs"
                            output_dir.mkdir(exist_ok=True)
                            output_file = output_dir / f"cmd_{int(time.time())}_{cmd_index}.txt"
                            
                            print(f"{Colors.CYAN}⏱️  Detected long-running command with more tasks queued. Opening in new controlled terminal for parallel execution...{Colors.RESET}\n")
                            type_command(command)
                            terminal_id = open_new_terminal(command, split=False, output_file=str(output_file))
                            command_history.append({
                                'command': command,
                                'exit_code': 0,
                                'output': f'Running in new controlled terminal window',
                                'type': 'new_terminal',
                                'parallel': True,
                                'output_file': str(output_file),
                                'terminal_id': terminal_id,
                                'controlled': True
                            })
                            print(f"{Colors.GREEN}✓ Terminal ID: {terminal_id} (AI can control this terminal){Colors.RESET}")
                            print(f"{Colors.GREEN}✓ Command running in new terminal (parallel execution){Colors.RESET}")
                            print(f"{Colors.CYAN}   Output will be saved to: {output_file}{Colors.RESET}\n")
                            time.sleep(0.3)  # Small delay to allow terminal to open
                        elif is_long_running_command(command) and not has_more_commands:
                            # Long-running but no more commands - execute normally with timeout
                            timeout = 180
                            print(f"{Colors.CYAN}⏱️  Detected long-running command. Will continue after {timeout}s if needed...{Colors.RESET}\n")
                            
                            # Check if command exists
                            exists, tool_name = check_command_exists(command)
                            if not exists and tool_name:
                                print(f"{Colors.YELLOW}⚠️  Warning: Tool '{tool_name}' may not be available{Colors.RESET}")
                                print(f"{Colors.YELLOW}Attempting to execute anyway...{Colors.RESET}\n")
                            
                            exit_code, output = execute_command_live(command, timeout=timeout, capture_output=True)
                            
                            # Check for "command not found" errors
                            if exit_code == 127 or ('command not found' in output.lower() or '/bin/sh:' in output.lower()):
                                suggestion = suggest_alternative(command, output)
                                if suggestion:
                                    print(f"{Colors.CYAN}💡 {suggestion}{Colors.RESET}\n")
                            
                            # Store in history
                            command_history.append({
                                'command': command,
                                'exit_code': exit_code,
                                'output': output,
                                'type': 'execute'
                            })
                            
                            if exit_code != 0:
                                print(f"{Colors.YELLOW}⚠️  Command exited with code {exit_code}{Colors.RESET}")
                            print()
                        else:
                            # Check if this command should go to an existing controlled terminal
                            existing_terminal_id = find_controlled_terminal_for_command(command, command_history)
                            
                            if existing_terminal_id:
                                # Send command to existing controlled terminal
                                print(f"{Colors.CYAN}📤 Sending command to controlled terminal ({existing_terminal_id})...{Colors.RESET}\n")
                                type_command(command)
                                if send_command_to_terminal(existing_terminal_id, command):
                                    print(f"{Colors.GREEN}✓ Command sent to terminal{Colors.RESET}")
                                    time.sleep(1)
                                    output = read_terminal_output(existing_terminal_id)
                                    command_history.append({
                                        'command': command,
                                        'exit_code': 0,
                                        'output': output,
                                        'type': 'execute',
                                        'sent_to_terminal': existing_terminal_id
                                    })
                                    if output:
                                        print(f"{Colors.CYAN}Output from terminal:{Colors.RESET}")
                                        print(output[-500:] if len(output) > 500 else output)
                                    print()
                                    continue
                            
                            # Check if it's an interactive command BEFORE executing
                            if is_interactive_command(command):
                                print(f"{Colors.YELLOW}⚠️  Detected interactive program{Colors.RESET}")
                                suggestion = suggest_non_interactive_alternative(command)
                                print(f"{Colors.CYAN}💡 {suggestion}{Colors.RESET}")
                                print(f"{Colors.MAGENTA}🪟 Opening in new controlled terminal...{Colors.RESET}\n")
                                
                                # Open in new controlled terminal
                                type_command(command)
                                terminal_id = open_new_terminal(command, split=False)
                                command_history.append({
                                    'command': command,
                                    'exit_code': 0,
                                    'output': 'Opened in new controlled terminal (interactive program)',
                                    'type': 'new_terminal',
                                    'interactive': True,
                                    'terminal_id': terminal_id,
                                    'controlled': True
                                })
                                print(f"{Colors.GREEN}✓ Interactive program opened in controlled terminal (ID: {terminal_id}){Colors.RESET}")
                                print(f"{Colors.CYAN}   AI can send commands to this terminal{Colors.RESET}\n")
                                time.sleep(0.3)
                                continue
                            
                            # Use shorter timeout for potentially problematic commands
                            timeout = 15 if 'msfconsole' in command.lower() else 60
                            
                            # Check if command exists
                            exists, tool_name = check_command_exists(command)
                            if not exists and tool_name:
                                print(f"{Colors.YELLOW}⚠️  Warning: Tool '{tool_name}' may not be available{Colors.RESET}")
                                print(f"{Colors.YELLOW}Attempting to execute anyway...{Colors.RESET}\n")
                            
                            exit_code, output = execute_command_live(command, timeout=timeout, capture_output=True)
                            
                            # Extract subdomains/domains and add to /etc/hosts
                            subdomains = extract_subdomains_and_ips(output)
                            for subdomain_info in subdomains:
                                domain = subdomain_info['domain']
                                ip = subdomain_info['ip']
                                if add_to_hosts_file(domain, ip):
                                    print(f"{Colors.GREEN}✓ Added {domain} -> {ip} to /etc/hosts{Colors.RESET}")
                                else:
                                    print(f"{Colors.YELLOW}⚠️  Could not add {domain} to /etc/hosts (may need sudo){Colors.RESET}")
                            
                            # Check for "command not found" errors
                            if exit_code == 127 or ('command not found' in output.lower() or '/bin/sh:' in output.lower()):
                                suggestion = suggest_alternative(command, output)
                                if suggestion:
                                    print(f"{Colors.CYAN}💡 {suggestion}{Colors.RESET}\n")
                            
                            # Store in history
                            command_history.append({
                                'command': command,
                                'exit_code': exit_code,
                                'output': output,
                                'type': 'execute',
                                'subdomains_found': subdomains
                            })
                            
                            if exit_code != 0:
                                print(f"{Colors.YELLOW}⚠️  Command exited with code {exit_code}{Colors.RESET}")
                            print()
                
                # After executing all commands, intelligently suggest next steps
                print(f"{Colors.BOLD}{Colors.MAGENTA}🧠 Analyzing results and determining next steps...{Colors.RESET}\n")
                next_commands = ask_ai_for_next_steps(api_key, command_history, max_iterations=3)
                
                iteration = 0
                max_auto_iterations = 3  # Limit automatic iterations
                
                while next_commands and iteration < max_auto_iterations:
                    iteration += 1
                    print(f"{Colors.CYAN}💡 Suggested next steps (iteration {iteration}/{max_auto_iterations}):{Colors.RESET}\n")
                    
                    # Execute suggested commands
                    for cmd_info in next_commands:
                        cmd_type = cmd_info['type']
                        command = cmd_info['command']
                        
                        if not command:
                            continue
                        
                        # Safety check
                        if is_dangerous_command(command):
                            print(f"\n{Colors.YELLOW}⚠️  Warning: Potentially dangerous command detected{Colors.RESET}")
                            print(f"{Colors.YELLOW}Command: {command}{Colors.RESET}")
                            response = input(f"{Colors.YELLOW}Execute anyway? (yes/no): {Colors.RESET}").strip().lower()
                            if response != 'yes':
                                print(f"{Colors.RED}Skipping dangerous command.{Colors.RESET}\n")
                                continue
                        
                        if cmd_type == 'new_terminal':
                            print(f"\n{Colors.MAGENTA}🪟 Opening new controlled terminal window...{Colors.RESET}")
                            terminal_id = open_new_terminal(command, split=False)
                            time.sleep(0.5)
                            command_history.append({
                                'command': command,
                                'exit_code': 0,
                                'output': 'Opened in new controlled terminal',
                                'type': 'new_terminal',
                                'terminal_id': terminal_id,
                                'controlled': True
                            })
                            print(f"{Colors.GREEN}✓ Terminal ID: {terminal_id} (AI can control this terminal){Colors.RESET}\n")
                        elif cmd_type == 'split_terminal':
                            print(f"\n{Colors.MAGENTA}📑 Splitting terminal...{Colors.RESET}")
                            open_new_terminal(command, split=True)
                            time.sleep(0.5)
                            command_history.append({
                                'command': command,
                                'exit_code': 0,
                                'output': 'Opened in split terminal',
                                'type': 'split_terminal'
                            })
                        else:
                            # Check if this command should go to an existing controlled terminal
                            existing_terminal_id = find_controlled_terminal_for_command(command, command_history)
                            
                            if existing_terminal_id:
                                # Send command to existing controlled terminal
                                print(f"{Colors.CYAN}📤 Sending command to controlled terminal ({existing_terminal_id})...{Colors.RESET}\n")
                                type_command(command)
                                if send_command_to_terminal(existing_terminal_id, command):
                                    print(f"{Colors.GREEN}✓ Command sent to terminal{Colors.RESET}")
                                    time.sleep(1)
                                    output = read_terminal_output(existing_terminal_id)
                                    command_history.append({
                                        'command': command,
                                        'exit_code': 0,
                                        'output': output,
                                        'type': 'execute',
                                        'sent_to_terminal': existing_terminal_id
                                    })
                                    if output:
                                        print(f"{Colors.CYAN}Output from terminal:{Colors.RESET}")
                                        print(output[-500:] if len(output) > 500 else output)
                                    print()
                                    continue
                            
                            # Check if it's an interactive command BEFORE executing
                            if is_interactive_command(command):
                                print(f"{Colors.YELLOW}⚠️  Detected interactive program{Colors.RESET}")
                                suggestion = suggest_non_interactive_alternative(command)
                                print(f"{Colors.CYAN}💡 {suggestion}{Colors.RESET}")
                                print(f"{Colors.MAGENTA}🪟 Opening in new controlled terminal...{Colors.RESET}\n")
                                
                                # Open in new controlled terminal
                                type_command(command)
                                terminal_id = open_new_terminal(command, split=False)
                                command_history.append({
                                    'command': command,
                                    'exit_code': 0,
                                    'output': 'Opened in new controlled terminal (interactive program)',
                                    'type': 'new_terminal',
                                    'interactive': True,
                                    'terminal_id': terminal_id,
                                    'controlled': True
                                })
                                print(f"{Colors.GREEN}✓ Interactive program opened in controlled terminal (ID: {terminal_id}){Colors.RESET}")
                                print(f"{Colors.CYAN}   AI can send commands to this terminal{Colors.RESET}\n")
                                time.sleep(0.3)
                                continue
                            
                            # Execute command
                            # Use shorter timeout for potentially problematic commands
                            if 'msfconsole' in command.lower():
                                timeout = 15  # Very short timeout for msfconsole
                            else:
                                timeout = 180 if is_long_running_command(command) else 60
                            
                            exists, tool_name = check_command_exists(command)
                            if not exists and tool_name:
                                print(f"{Colors.YELLOW}⚠️  Warning: Tool '{tool_name}' may not be available{Colors.RESET}")
                                print(f"{Colors.YELLOW}Attempting to execute anyway...{Colors.RESET}\n")
                            
                            exit_code, output = execute_command_live(command, timeout=timeout, capture_output=True)
                            
                            # Extract subdomains/domains and add to /etc/hosts
                            subdomains = extract_subdomains_and_ips(output)
                            for subdomain_info in subdomains:
                                domain = subdomain_info['domain']
                                ip = subdomain_info['ip']
                                if add_to_hosts_file(domain, ip):
                                    print(f"{Colors.GREEN}✓ Added {domain} -> {ip} to /etc/hosts{Colors.RESET}")
                                else:
                                    print(f"{Colors.YELLOW}⚠️  Could not add {domain} to /etc/hosts (may need sudo){Colors.RESET}")
                            
                            if exit_code == 127 or ('command not found' in output.lower() or '/bin/sh:' in output.lower()):
                                suggestion = suggest_alternative(command, output)
                                if suggestion:
                                    print(f"{Colors.CYAN}💡 {suggestion}{Colors.RESET}\n")
                            
                            command_history.append({
                                'command': command,
                                'exit_code': exit_code,
                                'output': output,
                                'type': 'execute',
                                'subdomains_found': subdomains
                            })
                            
                            if exit_code != 0:
                                print(f"{Colors.YELLOW}⚠️  Command exited with code {exit_code}{Colors.RESET}")
                            print()
                    
                    # Ask for next steps again
                    if iteration < max_auto_iterations:
                        print(f"{Colors.BOLD}{Colors.MAGENTA}🧠 Analyzing latest results...{Colors.RESET}\n")
                        next_commands = ask_ai_for_next_steps(api_key, command_history, max_iterations=2)
                    else:
                        break
                
                if iteration > 0:
                    print(f"{Colors.GREEN}✓ Completed {iteration} iteration(s) of intelligent next-step suggestions{Colors.RESET}")
                    print(f"{Colors.CYAN}💡 You can continue manually or ask for more steps{Colors.RESET}\n")
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
    parser = argparse.ArgumentParser(
        description='Terminal AI - AI-powered terminal assistant with live execution',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  terminal-ai "list all files in current directory"
  terminal-ai "create a new Python project"
  terminal-ai --interactive
        """
    )
    
    parser.add_argument(
        'prompt',
        nargs='?',
        help='Your task or question'
    )
    
    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='Start interactive mode (default if no prompt)'
    )
    
    parser.add_argument(
        '--set-api-key',
        help='Set OpenAI API key'
    )
    
    # Check for common typos before parsing
    for arg in sys.argv:
        if arg in ['--interactivel', '--interactiv', '--interactve', '--interactie']:
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
