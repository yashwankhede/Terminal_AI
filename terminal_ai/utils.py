"""
Utility functions for Terminal AI
Command detection, system info, wordlist discovery, etc.
"""

import os
import sys
import re
import subprocess
import time
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from terminal_ai.config import Colors, CONFIG_DIR

logger = logging.getLogger(__name__)


def type_command(command: str, speed: float = 0.02) -> None:
    """Animate typing a command"""
    print(f"{Colors.CYAN}${Colors.RESET} ", end="", flush=True)
    for char in command:
        print(char, end="", flush=True)
        time.sleep(speed)
    print()  # New line after command


def is_long_running_command(command: str) -> bool:
    """Detect if a command is likely to run for a long time"""
    long_running_patterns = [
        r"\bnmap\b",  # Any nmap command
        r"\bmasscan\b",
        r"\brustscan\b",
        r"\benum4linux\b",
        r"\bkerbrute\b",
        r"\bhydra\b",
        r"\bmedusa\b",
        r"\bgobuster\b",
        r"\bdirb\b",
        r"\bdirsearch\b",
        r"\bffuf\b",
        r"\bnikto\b",
        r"\bsqlmap\b",
        r"\bping\b.*-t",
        r"\btail\s+-f",
        r"\bwatch\b",
        r"\btop\b",
        r"\bhtop\b",
        r"\bwhile\s+true",
        r">\s+/dev/tty",
        r"\bscan\b",  # Any scan command
        r"\benum\b",  # Any enumeration
    ]

    command_lower = command.lower().strip()
    for pattern in long_running_patterns:
        if re.search(pattern, command_lower):
            logger.debug(f"Detected long-running command: {command}")
            return True
    return False


def should_run_in_background(command: str) -> bool:
    """Determine if a command should run in background"""
    background_patterns = [
        r"\bnmap\s+-p-",  # Full port scans
        r"\bnohup\b",
        r"\b&\s*$",  # Already has & at end
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
        r"\bmsfconsole\b",  # msfconsole is always interactive unless -x is used
        r"\bpython\s*$",  # python without -c or script
        r"^\s*python3\s*$",
        r"^\s*ruby\s*$",
        r"^\s*irb\s*$",
        r"^\s*bash\s*$",  # bash without -c
        r"^\s*sh\s*$",
        r"^\s*zsh\s*$",
        r"^\s*fish\s*$",
    ]

    # Check for always interactive programs first
    for pattern in always_interactive:
        if re.search(pattern, command_lower):
            # msfconsole with -x flag is non-interactive
            if "msfconsole" in command_lower and "-x" in command_lower:
                return False
            logger.debug(f"Detected interactive command: {command}")
            return True

    # Conditionally interactive programs
    conditionally_interactive = [
        r"^\s*mysql\s*$",  # mysql without -e or script
        r"^\s*psql\s*$",  # psql without -c or -f
        r"^\s*sqlite3\s+[^-]",  # sqlite3 without -cmd
        r"^\s*nc\s+[^-]",  # netcat in listen mode
        r"^\s*netcat\s+[^-]",
    ]

    command_stripped = command.strip()
    for pattern in conditionally_interactive:
        if re.search(pattern, command_stripped, re.IGNORECASE):
            return True

    # Check for non-interactive flags that make it non-interactive
    non_interactive_flags = ["-x", "-c", "-e", "-f", "-r", "--execute", "--file", "--resource"]
    for flag in non_interactive_flags:
        if flag in command_lower:
            return False  # Has non-interactive flag

    return False


def suggest_non_interactive_alternative(command: str) -> str:
    """Suggest non-interactive alternative for interactive commands"""
    command_lower = command.lower().strip()

    if "msfconsole" in command_lower:
        return "Use: msfconsole -q -x 'use exploit/...; set RHOSTS ...; exploit' or open in new terminal"
    elif "mysql" in command_lower:
        return "Use: mysql -e 'SELECT ...' or mysql < script.sql"
    elif "psql" in command_lower:
        return "Use: psql -c 'SELECT ...' or psql -f script.sql"
    elif "python" in command_lower or "python3" in command_lower:
        return "Use: python -c 'code' or python script.py"
    elif "bash" in command_lower or "sh" in command_lower:
        return "Use: bash -c 'command' or bash script.sh"

    return "This is an interactive program. Consider using non-interactive flags or opening in a new terminal."


def is_dangerous_command(command: str) -> bool:
    """Check if a command is potentially dangerous"""
    dangerous_patterns = [
        r"\brm\s+-rf\s+/",
        r"\bdd\s+if=",
        r"\bformat\s+",
        r"\bmkfs\s+",
        r">\s+/dev/sd",
        r"\bsudo\s+rm\s+-rf",
    ]

    command_lower = command.lower().strip()
    for pattern in dangerous_patterns:
        if re.search(pattern, command_lower):
            logger.warning(f"Detected dangerous command: {command}")
            return True
    return False


def check_command_exists(command: str) -> Tuple[bool, str]:
    """
    Check if a command/tool exists in the system
    Returns: (exists, tool_name)
    """
    # Extract the first word (command name) from the command string
    parts = command.strip().split()
    if not parts:
        return False, ""

    # Get the base command (first word, excluding special chars)
    base_cmd = parts[0]

    # Remove any special characters and path separators
    base_cmd = re.sub(r"[;&|<>/]", "", base_cmd)

    if not base_cmd:
        return False, ""

    # Check using command -v (POSIX standard)
    try:
        result = subprocess.run(
            ["command", "-v", base_cmd], shell=False, capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0 and result.stdout.strip():
            return True, base_cmd
    except Exception as e:
        logger.debug(f"Error checking command existence: {e}")

    # Fallback to which
    try:
        result = subprocess.run(
            ["which", base_cmd], shell=False, capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0 and result.stdout.strip():
            return True, base_cmd
    except Exception as e:
        logger.debug(f"Error with which: {e}")

    return False, base_cmd


def find_wordlists() -> Dict[str, str]:
    """Find available wordlists/SecLists in common locations"""
    wordlists = {}

    # Common wordlist locations
    common_locations = [
        "/usr/share/wordlists",
        "/usr/share/seclists",
        "/opt/SecLists",
        "~/SecLists",
        "~/wordlists",
        "/usr/share/dirb/wordlists",
        "/usr/share/dirbuster/wordlists",
    ]

    # Common wordlist files to look for
    wordlist_patterns = [
        ("directory-list-2.3-medium.txt", "dirbuster-medium"),
        ("directory-list-2.3-big.txt", "dirbuster-big"),
        ("directory-list-2.3-small.txt", "dirbuster-small"),
        ("Discovery/DNS/subdomains-top1million-110000.txt", "seclists-dns-top1m"),
        ("Discovery/DNS/subdomains-top1million-5000.txt", "seclists-dns-top5k"),
        ("Discovery/Web-Content/directory-list-2.3-medium.txt", "seclists-dir-medium"),
        ("Discovery/Web-Content/raft-medium-directories.txt", "seclists-raft-medium-dirs"),
        ("Discovery/Web-Content/raft-medium-files.txt", "seclists-raft-medium-files"),
        ("Discovery/Web-Content/big.txt", "seclists-big"),
        ("Discovery/Web-Content/common.txt", "seclists-common"),
        (
            "Passwords/Common-Credentials/10-million-password-list-top-1000000.txt",
            "seclists-passwords-top1m",
        ),
        ("Usernames/xato-net-10-million-usernames.txt", "seclists-usernames-xato"),
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
            try:
                for root, dirs, files in os.walk(expanded_location):
                    for file in files:
                        if (
                            "directory-list" in file.lower()
                            or "common.txt" in file.lower()
                            or "big.txt" in file.lower()
                        ):
                            full_path = os.path.join(root, file)
                            key = f"wordlist-{os.path.basename(root)}-{file}"
                            if key not in wordlists:
                                wordlists[key] = full_path
            except Exception as e:
                logger.debug(f"Error walking {expanded_location}: {e}")

    logger.debug(f"Found {len(wordlists)} wordlists")
    return wordlists


def get_available_wordlists_info() -> str:
    """Get formatted string of available wordlists"""
    wordlists = find_wordlists()
    if not wordlists:
        return "None detected. Consider installing SecLists or other wordlists."

    info = []
    for key, path in sorted(wordlists.items()):
        info.append(f"{key}: {path}")

    return "\n".join(info)


def extract_subdomains_and_ips(output: str) -> List[Dict[str, str]]:
    """Extract subdomains and their IPs from command output"""
    results = []

    # Pattern to match subdomains/domains with IPs
    patterns = [
        # DNS output patterns
        (r"(\S+\.htb|\S+\.local|\S+\.internal)\s+(\d+\.\d+\.\d+\.\d+)", "dns"),
        (r"(\d+\.\d+\.\d+\.\d+)\s+(\S+\.htb|\S+\.local|\S+\.internal)", "reverse"),
        # Nmap output
        (
            r"Nmap scan report for (\S+\.htb|\S+\.local|\S+\.internal)\s+\((\d+\.\d+\.\d+\.\d+)\)",
            "nmap",
        ),
        # dig/nslookup output
        (r"(\S+\.htb|\S+\.local|\S+\.internal)\.\s+\d+\s+IN\s+A\s+(\d+\.\d+\.\d+\.\d+)", "dig"),
        # Generic domain patterns
        (r"(\S+\.(?:htb|local|internal|test|dev))\s+.*?(\d+\.\d+\.\d+\.\d+)", "generic"),
    ]

    for pattern, source in patterns:
        matches = re.finditer(pattern, output, re.IGNORECASE)
        for match in matches:
            if len(match.groups()) >= 2:
                domain = match.group(1).strip()
                ip = match.group(2).strip()
                # Validate IP
                if re.match(r"^\d+\.\d+\.\d+\.\d+$", ip):
                    results.append({"domain": domain, "ip": ip, "source": source})

    # Also look for domains mentioned in commands
    command_pattern = r"(\S+\.(?:htb|local|internal|test|dev))"
    domain_matches = re.findall(command_pattern, output, re.IGNORECASE)
    for domain in domain_matches:
        # Try to find associated IP from context
        ip_pattern = rf"{re.escape(domain)}.*?(\d+\.\d+\.\d+\.\d+)"
        ip_match = re.search(ip_pattern, output, re.IGNORECASE)
        if ip_match:
            ip = ip_match.group(1)
            results.append({"domain": domain, "ip": ip, "source": "context"})

    logger.debug(f"Extracted {len(results)} subdomain-IP pairs")
    return results


def add_to_hosts_file(domain: str, ip: str) -> bool:
    """Add domain to /etc/hosts file"""
    hosts_file = Path("/etc/hosts")

    # Check if entry already exists
    try:
        if hosts_file.exists():
            with open(hosts_file, "r") as f:
                content = f.read()
                if domain in content and ip in content:
                    logger.debug(f"Entry {domain} -> {ip} already exists in /etc/hosts")
                    return True  # Already exists
    except Exception as e:
        logger.debug(f"Error checking /etc/hosts: {e}")

    # Add entry (requires sudo)
    entry = f"{ip}\t{domain}\n"

    try:
        # Try to add without sudo first (might work if user has write access)
        with open(hosts_file, "a") as f:
            f.write(entry)
        logger.info(f"Added {domain} -> {ip} to /etc/hosts")
        return True
    except PermissionError:
        # Need sudo
        try:
            result = subprocess.run(
                ["sudo", "sh", "-c", f'echo "{entry}" >> {hosts_file}'],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                logger.info(f"Added {domain} -> {ip} to /etc/hosts (with sudo)")
                return True
            else:
                logger.warning(f"Failed to add {domain} to /etc/hosts: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error adding to /etc/hosts: {e}")
            return False
    except Exception as e:
        logger.error(f"Error adding to /etc/hosts: {e}")
        return False


def get_available_tools() -> str:
    """Get list of commonly used security/recon tools that are available"""
    tools = []
    common_tools = [
        "nmap",
        "masscan",
        "rustscan",
        "enum4linux",
        "smbclient",
        "smbmap",
        "crackmapexec",
        "kerbrute",
        "impacket-scripts",
        "ldapsearch",
        "ldapdomaindump",
        "dig",
        "nslookup",
        "host",
        "nikto",
        "gobuster",
        "dirb",
        "dirsearch",
        "ffuf",
        "sqlmap",
        "hydra",
        "medusa",
        "metasploit",
        "msfconsole",
        "nuclei",
        "gau",
        "waybackurls",
    ]

    for tool in common_tools:
        exists, _ = check_command_exists(tool)
        if exists:
            tools.append(tool)

    result = ", ".join(tools) if tools else "None detected"
    logger.debug(f"Available tools: {result}")
    return result


def suggest_alternative(command: str, output: str) -> str:
    """Suggest alternative commands when a tool is not found"""
    command_lower = command.lower()

    # Map missing tools to alternatives
    alternatives = {
        "enum4linux": "smbclient, smbmap, or crackmapexec",
        "kerbrute": "impacket-GetNPUsers or manual Kerberos enumeration",
        "crackmapexec": "smbclient or smbmap",
        "ldapdomaindump": "ldapsearch with manual parsing",
    }

    for tool, alt in alternatives.items():
        if tool in command_lower:
            return f"Alternative: Use {alt} instead"

    # Check for "command not found" errors
    if "command not found" in output.lower() or "not found" in output.lower():
        tool_name = command.split()[0] if command.split() else ""
        return (
            f"Tool '{tool_name}' not found. Consider installing it or using built-in alternatives."
        )

    return ""


def get_system_info() -> str:
    """Get system information for context"""
    info = []

    # OS info
    if sys.platform == "darwin":
        info.append(f"OS: macOS")
        try:
            result = subprocess.run(["sw_vers"], capture_output=True, text=True, timeout=2)
            info.append(result.stdout.strip())
        except Exception as e:
            logger.debug(f"Error getting macOS version: {e}")
    elif sys.platform.startswith("linux"):
        info.append(f"OS: Linux")
        try:
            result = subprocess.run(["uname", "-a"], capture_output=True, text=True, timeout=2)
            info.append(result.stdout.strip())
        except Exception as e:
            logger.debug(f"Error getting Linux info: {e}")

    # Current directory
    try:
        info.append(f"Current directory: {os.getcwd()}")
    except Exception as e:
        logger.debug(f"Error getting current directory: {e}")

    # User info
    info.append(f"User: {os.getenv('USER', 'unknown')}")

    # Shell
    info.append(f"Shell: {os.getenv('SHELL', 'unknown')}")

    return "\n".join(info)
