"""
Tests for utility functions
"""

import pytest
from terminal_ai.utils import (
    is_long_running_command,
    is_interactive_command,
    is_dangerous_command,
    check_command_exists,
    extract_subdomains_and_ips
)


def test_is_long_running_command():
    """Test detection of long-running commands"""
    assert is_long_running_command("nmap -sC -sV 10.0.0.1") == True
    assert is_long_running_command("gobuster dir -u http://example.com") == True
    assert is_long_running_command("ls -la") == False
    assert is_long_running_command("echo hello") == False


def test_is_interactive_command():
    """Test detection of interactive commands"""
    assert is_interactive_command("msfconsole") == True
    assert is_interactive_command("python") == True
    assert is_interactive_command("msfconsole -q -x 'use exploit'") == False
    assert is_interactive_command("ls -la") == False


def test_is_dangerous_command():
    """Test detection of dangerous commands"""
    assert is_dangerous_command("rm -rf /") == True
    assert is_dangerous_command("sudo rm -rf /tmp") == True
    assert is_dangerous_command("ls -la") == False
    assert is_dangerous_command("echo hello") == False


def test_check_command_exists():
    """Test command existence checking"""
    exists, name = check_command_exists("ls")
    assert exists == True
    assert name == "ls"
    
    exists, name = check_command_exists("nonexistent_command_xyz")
    assert exists == False


def test_extract_subdomains_and_ips():
    """Test subdomain and IP extraction"""
    output = "Nmap scan report for dc.active.htb (10.129.222.192)"
    results = extract_subdomains_and_ips(output)
    assert len(results) > 0
    assert any(r['domain'] == 'dc.active.htb' for r in results)
    assert any(r['ip'] == '10.129.222.192' for r in results)

