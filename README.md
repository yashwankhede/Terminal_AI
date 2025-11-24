# Terminal AI

An AI-powered terminal assistant that can help you with terminal commands, system tasks, and automation. Built with OpenAI's GPT models.

## Features

- 🤖 **AI-Powered Assistance**: Get help with terminal commands and system tasks
- 💬 **Interactive Mode**: Continuous conversation mode for complex tasks
- ⚡ **Live Command Execution**: Commands execute automatically with real-time output streaming
- 🎬 **Visual Feedback**: See commands being typed and executed in real-time
- 🪟 **Multi-Terminal Support**: Automatically opens new terminal windows or splits when needed
- 🔒 **Secure Configuration**: API keys stored securely with proper permissions
- 🛠️ **System Integration**: Works with your existing terminal environment

## Installation

### Quick Install

1. Clone or download this repository
2. Run the installation script:

```bash
chmod +x install.sh
./install.sh
```

The installation script will:
- Check for Python 3 and pip
- Install required dependencies
- Prompt for your OpenAI API key
- Install the tool to `/usr/local/bin` (requires sudo)
- Guide you through permission setup

### Manual Installation

1. Install dependencies:
```bash
pip3 install -r requirements.txt
```

2. Set your OpenAI API key:
```bash
python3 terminal_ai.py --set-api-key YOUR_API_KEY
```

3. Make the script executable:
```bash
chmod +x terminal_ai.py
```

4. Add to PATH (optional):
```bash
sudo ln -s $(pwd)/terminal_ai.py /usr/local/bin/terminal-ai
```

## Usage

### Basic Usage

Describe what you want to do, and Terminal AI will execute the commands automatically:
```bash
terminal-ai "list all files in the current directory"
terminal-ai "show me disk usage"
terminal-ai "create a new Python project called myapp"
```

Commands are executed **live** in your terminal with real-time output streaming. You'll see:
- Commands being typed (animated)
- Real-time output as commands execute
- Automatic execution of command sequences

### Interactive Mode

Start an interactive session for continuous control:
```bash
terminal-ai --interactive
# or
terminal-ai -i
```

In interactive mode:
- Type your requests naturally - commands execute automatically
- Use `exit` or `quit` to leave
- Use `help` for available commands
- Use `execute <command>` to run a command directly
- Terminal AI maintains context across your session

### How It Works

1. **You describe what you want**: "create a backup of my Documents folder"
2. **AI generates commands**: Terminal AI analyzes your request and creates the necessary commands
3. **Commands execute live**: You see commands being typed and executed in real-time
4. **Multi-step tasks**: Complex tasks are broken into sequential commands
5. **New terminals**: If needed, Terminal AI opens new terminal windows or splits

### Safety Features

- **Dangerous command detection**: Commands that could cause data loss are flagged
- **Confirmation prompts**: You'll be asked to confirm potentially dangerous operations
- **Real-time feedback**: See exactly what's happening at each step

## Permissions

### macOS

The tool may need:
- **Full Disk Access**: For file operations across the system
- **Terminal Access**: For command execution
- **sudo access**: For system-level operations

To grant permissions:
1. Open **System Settings** > **Privacy & Security**
2. Add your terminal app (Terminal, iTerm2, etc.) to:
   - Full Disk Access
   - Automation (if needed)

### Linux

The tool may need:
- **sudo access**: For system operations
- **Execution permissions**: Already handled during installation

## Configuration

Configuration is stored in `~/.terminal_ai/config.json` with secure permissions (600).

### Update API Key

```bash
terminal-ai --set-api-key YOUR_NEW_API_KEY
```

### View Configuration

```bash
cat ~/.terminal_ai/config.json
```

## Examples

### File Operations
```bash
# Terminal AI will execute: find . -name "*.py"
terminal-ai "find all Python files in my project"

# Terminal AI will create the backup
terminal-ai "create a backup of my Documents folder"
```

### System Information
```bash
# Terminal AI executes: df -h, top, etc.
terminal-ai "show me disk usage and system stats"
```

### Development Tasks
```bash
# Terminal AI creates venv and installs packages
terminal-ai "set up a Python virtual environment and install requests"

# Terminal AI creates project structure
terminal-ai "create a new Flask project with app.py and requirements.txt"
```

### Complex Multi-Step Tasks
```bash
terminal-ai --interactive
# Then describe complex workflows:
# "Set up a new Node.js project, install Express, and create a basic server"
# Terminal AI will execute all steps automatically
```

### Opening New Terminals
Terminal AI can automatically open new terminal windows when needed:
- Long-running processes
- Monitoring tasks
- Parallel operations

## Safety Features

- **Dangerous Command Detection**: Automatically flags potentially destructive commands
- **Confirmation Prompts**: Asks for confirmation before executing risky operations
- **Timeout Protection**: Commands timeout after 5 minutes
- **Secure Storage**: API keys stored with restricted permissions (600)
- **Error Handling**: Graceful error handling with clear error messages
- **Real-time Monitoring**: See exactly what's happening at each step

## Requirements

- Python 3.7+
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))
- Internet connection (for API calls)

## Troubleshooting

### Command not found
If `terminal-ai` is not found after installation:
```bash
# Restart your terminal or run:
source ~/.zshrc  # or ~/.bashrc

# Or use the full path:
/usr/local/bin/terminal-ai
```

### API Key Issues
```bash
# Check if API key is set:
terminal-ai --set-api-key YOUR_KEY

# Verify configuration:
cat ~/.terminal_ai/config.json
```

### Permission Issues
- Ensure the script is executable: `chmod +x terminal_ai.py`
- Check file permissions: `ls -l terminal_ai.py`
- For system operations, ensure sudo access is configured

## Security Notes

⚠️ **Important Security Considerations:**

1. **API Key Security**: Your API key is stored locally with restricted permissions. Never share it.

2. **Automatic Execution**: Terminal AI executes commands automatically. Review what's happening in real-time and use Ctrl+C to interrupt if needed.

3. **Sudo Access**: Be cautious when granting sudo access. The tool will prompt for confirmation.

4. **Network Usage**: The tool makes API calls to OpenAI. Review your network security policies.

5. **Data Privacy**: Commands and system information are sent to OpenAI API. Review OpenAI's privacy policy.

## License

This project is provided as-is for educational and personal use.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the error messages
3. Ensure all dependencies are installed
4. Verify your API key is correct

---

**Disclaimer**: This tool executes commands on your system. Use responsibly and always review commands before execution, especially when using the `--execute` flag.

