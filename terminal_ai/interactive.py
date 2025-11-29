"""
Interactive command handler using pexpect
Handles all interactive prompts automatically using AI
"""

import re
import logging
import time
from typing import Optional, Dict, List, Tuple, Any
from pathlib import Path

try:
    import pexpect
    PEXPECT_AVAILABLE = True
except ImportError:
    PEXPECT_AVAILABLE = False
    pexpect = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from terminal_ai.config import Colors, CONFIG_DIR
from terminal_ai.utils import extract_ssh_credentials

logger = logging.getLogger(__name__)


class InteractivePromptHandler:
    """
    Handles interactive prompts automatically using AI
    Acts as an overlay that monitors terminal output and responds intelligently
    """
    
    def __init__(self, api_key: str, user_context: str = "", command_history: List[Dict[str, Any]] = None):
        self.api_key = api_key
        self.user_context = user_context
        self.command_history = command_history or []
        self.credentials_cache: Dict[str, str] = {}
        
        # Extract credentials from context
        ssh_creds = extract_ssh_credentials(user_context)
        if ssh_creds:
            key = f"{ssh_creds['user']}@{ssh_creds['host']}"
            self.credentials_cache[key] = ssh_creds['password']
    
    def detect_prompt_type(self, output: str) -> Optional[Dict[str, Any]]:
        """
        Detect what type of prompt is being shown
        Returns: {'type': 'password'|'yesno'|'input'|'choice', 'message': '...', 'context': '...'}
        """
        output_lower = output.lower()
        last_lines = output.split('\n')[-5:]  # Last 5 lines
        recent_output = '\n'.join(last_lines).lower()
        
        # Password prompts
        password_patterns = [
            r'password:\s*$',
            r'enter password:\s*$',
            r'passphrase:\s*$',
            r'password for .+:\s*$',
            r'\[sudo\] password for .+:\s*$',
            r'password \(.+\):\s*$',
        ]
        
        for pattern in password_patterns:
            if re.search(pattern, output, re.IGNORECASE | re.MULTILINE):
                # Try to extract username/host from context
                username = None
                for line in last_lines:
                    if 'password for' in line.lower():
                        match = re.search(r'password for (.+?):', line, re.IGNORECASE)
                        if match:
                            username = match.group(1).strip()
                return {
                    'type': 'password',
                    'message': last_lines[-1] if last_lines else 'Password:',
                    'context': recent_output,
                    'username': username
                }
        
        # Yes/No prompts
        yesno_patterns = [
            r'\(y/n\)',
            r'\[y/n\]',
            r'\(yes/no\)',
            r'\[yes/no\]',
            r'continue\?',
            r'proceed\?',
            r'are you sure',
        ]
        
        for pattern in yesno_patterns:
            if re.search(pattern, recent_output, re.IGNORECASE):
                return {
                    'type': 'yesno',
                    'message': last_lines[-1] if last_lines else 'Continue?',
                    'context': recent_output
                }
        
        # Input fields
        input_patterns = [
            r'enter .+:\s*$',
            r'input .+:\s*$',
            r'provide .+:\s*$',
            r'select .+:\s*$',
            r'>\s*$',  # Generic prompt
        ]
        
        for pattern in input_patterns:
            if re.search(pattern, recent_output, re.IGNORECASE):
                return {
                    'type': 'input',
                    'message': last_lines[-1] if last_lines else 'Input:',
                    'context': recent_output
                }
        
        # Interactive shell prompts (msfconsole, mysql, etc.)
        shell_prompts = [
            r'msf\d+\s*>',
            r'mysql>\s*',
            r'psql>\s*',
            r'>>>\s*',
            r'In \[\d+\]:\s*',
        ]
        
        for pattern in shell_prompts:
            if re.search(pattern, output, re.IGNORECASE):
                return {
                    'type': 'shell',
                    'message': 'Interactive shell prompt',
                    'context': recent_output
                }
        
        return None
    
    def get_password_from_context(self, prompt_info: Dict[str, Any]) -> Optional[str]:
        """Try to get password from cached credentials or context"""
        message = prompt_info.get('message', '').lower()
        username = prompt_info.get('username', '')
        
        # Check cached credentials
        if username:
            for key, password in self.credentials_cache.items():
                if username in key or key in message:
                    return password
        
        # Check SSH credentials from context
        ssh_creds = extract_ssh_credentials(self.user_context)
        if ssh_creds:
            return ssh_creds.get('password')
        
        # Check command history for credentials
        for entry in self.command_history:
            if 'credentials' in entry:
                return entry['credentials'].get('password')
        
        return None
    
    def ask_ai_for_response(self, prompt_info: Dict[str, Any], full_output: str) -> Optional[str]:
        """
        Use AI to determine the appropriate response to a prompt
        """
        if OpenAI is None:
            return None
        
        prompt_type = prompt_info.get('type')
        message = prompt_info.get('message', '')
        context = prompt_info.get('context', '')
        
        # Build context from command history
        history_summary = ""
        if self.command_history:
            recent = self.command_history[-3:]  # Last 3 commands
            history_summary = "\nRecent commands:\n"
            for entry in recent:
                history_summary += f"- {entry.get('command', 'N/A')}\n"
        
        system_prompt = f"""You are an autonomous terminal assistant that responds to interactive prompts automatically.

Current Situation:
- Command output: {full_output[-1000:]}  # Last 1000 chars
- Prompt detected: {message}
- Prompt type: {prompt_type}
- Context: {context}

{history_summary}

User's original request: {self.user_context}

INSTRUCTIONS:
1. Analyze the prompt and determine the appropriate response
2. For password prompts: Use credentials from context if available, otherwise respond with a reasonable default or empty string
3. For yes/no prompts: Respond "yes" or "y" if it helps accomplish the user's goal, "no" or "n" otherwise
4. For input prompts: Provide a reasonable value based on context
5. For shell prompts: Provide the next command to execute
6. Respond with ONLY the response text, no explanation

Respond with the exact text to send (e.g., "yes", "password123", "ls -la"):"""

        try:
            client = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"What should I respond to this prompt?\n\n{message}"}
                ],
                max_tokens=100,
                temperature=0.3
            )
            
            answer = response.choices[0].message.content.strip()
            logger.info(f"AI response to prompt: {answer[:50]}...")
            return answer
        except Exception as e:
            logger.error(f"Error getting AI response: {e}")
            return None
    
    def get_response(self, prompt_info: Dict[str, Any], full_output: str) -> Optional[str]:
        """
        Get the appropriate response for a prompt
        Tries multiple strategies: cached credentials -> AI -> defaults
        """
        prompt_type = prompt_info.get('type')
        
        # Password prompts - try credentials first
        if prompt_type == 'password':
            password = self.get_password_from_context(prompt_info)
            if password:
                logger.info("Using password from context")
                return password
            
            # Try AI
            ai_response = self.ask_ai_for_response(prompt_info, full_output)
            if ai_response:
                return ai_response
            
            # Default: empty (might work for some cases)
            logger.warning("No password found, using empty string")
            return ""
        
        # Yes/No prompts - use AI or default to yes
        elif prompt_type == 'yesno':
            ai_response = self.ask_ai_for_response(prompt_info, full_output)
            if ai_response:
                # Normalize to yes/no
                if ai_response.lower().startswith('y'):
                    return 'yes'
                elif ai_response.lower().startswith('n'):
                    return 'no'
            # Default to yes for most cases
            return 'yes'
        
        # Input prompts - use AI
        elif prompt_type == 'input':
            ai_response = self.ask_ai_for_response(prompt_info, full_output)
            return ai_response or ""
        
        # Shell prompts - use AI to get next command
        elif prompt_type == 'shell':
            ai_response = self.ask_ai_for_response(prompt_info, full_output)
            return ai_response
        
        return None


def execute_command_interactive(
    command: str,
    api_key: str,
    user_context: str = "",
    command_history: List[Dict[str, Any]] = None,
    timeout: int = 300,
    show_command: bool = True,
) -> Tuple[int, str]:
    """
    Execute a command with full interactive prompt handling
    Uses pexpect to monitor and respond to prompts automatically
    """
    if not PEXPECT_AVAILABLE:
        logger.warning("pexpect not available, falling back to regular execution")
        from terminal_ai.core import execute_command_live
        return execute_command_live(command, timeout=timeout, show_command=show_command)
    
    if show_command:
        from terminal_ai.utils import type_command
        type_command(command)
    
    handler = InteractivePromptHandler(api_key, user_context, command_history)
    output_lines = []
    
    try:
        # Start the process with pexpect
        child = pexpect.spawn(
            command,
            encoding='utf-8',
            timeout=timeout,
            maxread=10000
        )
        
        # Set logfile for debugging (optional)
        # child.logfile = sys.stdout
        
        start_time = time.time()
        last_output_time = time.time()
        no_output_timeout = 15  # 15 seconds without output
        
        while True:
            try:
                # Wait for output or prompt
                index = child.expect([
                    pexpect.EOF,  # Process ended
                    pexpect.TIMEOUT,  # Timeout
                    r'.+',  # Any output
                ], timeout=5)
                
                if index == 0:  # EOF - process ended
                    break
                elif index == 1:  # Timeout
                    # Check if we've had no output for too long
                    if time.time() - last_output_time > no_output_timeout:
                        # Try to detect if we're waiting for input
                        current_output = child.before if hasattr(child, 'before') else ''
                        prompt_info = handler.detect_prompt_type(current_output)
                        
                        if prompt_info:
                            response = handler.get_response(prompt_info, current_output)
                            if response:
                                logger.info(f"Auto-responding to prompt: {response[:20]}...")
                                print(f"\n{Colors.CYAN}🤖 AI responding to prompt automatically...{Colors.RESET}")
                                child.sendline(response)
                                last_output_time = time.time()
                                continue
                    
                    # Still no output - might be stuck
                    if time.time() - start_time > timeout:
                        logger.warning("Command timeout")
                        child.terminate()
                        break
                    continue
                else:  # Got output
                    output = child.before if hasattr(child, 'before') else ''
                    if output:
                        print(output, end='', flush=True)
                        output_lines.append(output)
                        last_output_time = time.time()
                        
                        # Check for prompts in the output
                        prompt_info = handler.detect_prompt_type(''.join(output_lines))
                        if prompt_info:
                            response = handler.get_response(prompt_info, ''.join(output_lines))
                            if response:
                                logger.info(f"Auto-responding to prompt: {response[:20]}...")
                                print(f"\n{Colors.CYAN}🤖 AI responding: {prompt_info.get('type', 'prompt')}{Colors.RESET}")
                                time.sleep(0.1)  # Small delay
                                child.sendline(response)
                                output_lines.append(f"\n[AI Response: {response}]\n")
                                last_output_time = time.time()
            
            except pexpect.EOF:
                break
            except pexpect.TIMEOUT:
                # Check for prompts in accumulated output
                current_output = ''.join(output_lines)
                prompt_info = handler.detect_prompt_type(current_output)
                
                if prompt_info:
                    response = handler.get_response(prompt_info, current_output)
                    if response:
                        logger.info(f"Auto-responding to timeout prompt: {response[:20]}...")
                        print(f"\n{Colors.CYAN}🤖 AI responding to prompt automatically...{Colors.RESET}")
                        child.sendline(response)
                        output_lines.append(f"\n[AI Response: {response}]\n")
                        last_output_time = time.time()
                        continue
                
                # Check overall timeout
                if time.time() - start_time > timeout:
                    logger.warning("Command timeout")
                    child.terminate()
                    break
        
        # Get final output
        child.close()
        exit_code = child.exitstatus if child.exitstatus is not None else 0
        
        final_output = ''.join(output_lines)
        logger.info(f"Interactive command completed with exit code: {exit_code}")
        return (exit_code, final_output)
    
    except Exception as e:
        error_msg = f"Error in interactive execution: {str(e)}"
        logger.error(error_msg)
        print(f"{Colors.RED}{error_msg}{Colors.RESET}")
        # Fallback to regular execution
        from terminal_ai.core import execute_command_live
        return execute_command_live(command, timeout=timeout, show_command=show_command)

