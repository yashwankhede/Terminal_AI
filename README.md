# Terminal_AI

**AI-powered terminal assistant that executes shell tasks from natural language instructions.**

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![CI Status](https://img.shields.io/badge/CI-passing-brightgreen.svg)](.github/workflows/tests.yml)
[![Version](https://img.shields.io/badge/version-0.1.0-orange.svg)](CHANGELOG.md)

---

## 🎬 Demo

<!-- TODO: Add demo GIF/video here -->
**Instructions for adding demo:**
1. Record a screen capture showing Terminal_AI in action
2. Convert to GIF (recommended: 800x600, <5MB)
3. Upload to repository or use a GIF hosting service
4. Replace this section with: `![Demo](path/to/demo.gif)`

---

## ✨ Features

- **🤖 Execute shell commands from natural language** - Just describe what you want, and Terminal_AI does it
- **🪟 Multi-terminal support** - Automatically opens new terminals for parallel tasks
- **💬 Interactive mode** - Continuous conversation with context awareness
- **🐍 Python API access** - Use Terminal_AI programmatically in your scripts
- **📝 Custom prompt profiles** - Configure AI behavior for different use cases
- **🛡️ Error-aware command generation** - Learns from failures and suggests alternatives
- **🔒 Secure execution confirmation** - Prompts for dangerous operations

---

## 🚀 60-Second Quickstart

```bash
# Clone the repository
git clone https://github.com/yashwankhede/Terminal_AI.git

# Navigate to the directory
cd Terminal_AI

# Install dependencies
pip install -r requirements.txt

# Run Terminal_AI
python terminal_ai_cli.py
```

**First-time setup:**
```bash
# Set your OpenAI API key
python terminal_ai_cli.py --set-api-key YOUR_API_KEY

# Or use interactive mode
python terminal_ai_cli.py --interactive
```

---

## 📖 Examples

### 1. Create a directory and move files

```bash
terminal-ai "create a directory called 'backup' and move all .log files there"
```

**What Terminal_AI does:**
- Creates the `backup` directory
- Finds all `.log` files
- Moves them to the backup directory
- Shows you the results

### 2. Search logs and parse output

```bash
terminal-ai "search for errors in /var/log/syslog from the last hour and show me the top 10"
```

**What Terminal_AI does:**
- Searches system logs for error entries
- Filters by timestamp (last hour)
- Extracts and displays the top 10 errors
- Formats output for readability

### 3. Install packages and configure environment

```bash
terminal-ai "set up a Python virtual environment, install Flask and requests, and create a basic app.py"
```

**What Terminal_AI does:**
- Creates a Python virtual environment
- Activates it
- Installs required packages
- Creates a basic Flask application structure

### 4. System monitoring commands

```bash
terminal-ai "show me disk usage, top 5 processes by CPU, and network connections"
```

**What Terminal_AI does:**
- Runs `df -h` for disk usage
- Executes `top` or `ps` for process monitoring
- Checks network connections with `netstat` or `ss`
- Combines results in a readable format

### 5. Git automation commands

```bash
terminal-ai "check git status, add all changes, commit with message 'Update features', and push to origin"
```

**What Terminal_AI does:**
- Checks current git status
- Stages all changes
- Creates a commit with your message
- Pushes to the remote repository

---

## 🤔 Why Terminal_AI?

| Feature | Conventional Shell | Shell-GPT Tools | Terminal_AI |
|---------|-------------------|-----------------|-------------|
| **Natural Language** | ❌ | ✅ | ✅ |
| **Context Awareness** | ❌ | ⚠️ Limited | ✅ Full |
| **Multi-Terminal** | ❌ Manual | ❌ | ✅ Automatic |
| **Error Recovery** | ❌ | ⚠️ Basic | ✅ Intelligent |
| **Interactive Mode** | ❌ | ⚠️ Limited | ✅ Full |
| **Learning from Failures** | ❌ | ❌ | ✅ |
| **Auto Next Steps** | ❌ | ❌ | ✅ |
| **Python API** | ❌ | ❌ | ✅ |

**vs. Manual Scripting:**
- **Faster**: No need to write scripts for one-off tasks
- **Smarter**: AI understands context and learns from mistakes
- **Safer**: Built-in dangerous command detection
- **More Flexible**: Adapts to your system and available tools

---

## 🗺️ Roadmap (0.1 → 1.0)

### Version 0.1 (Current)
- ✅ Basic command execution from natural language
- ✅ Interactive mode
- ✅ Multi-terminal support
- ✅ Error handling and recovery

### Version 0.2 (Planned)
- [ ] VSCode extension for integrated terminal control
- [ ] Plugin marketplace for custom commands
- [ ] Enhanced error messages with suggestions

### Version 0.3 (Planned)
- [ ] Auto-workflow builder for complex tasks
- [ ] Persistent memory profiles
- [ ] Command templates library

### Version 0.5 (Planned)
- [ ] Multi-user support
- [ ] Cloud sync for configurations
- [ ] Advanced analytics

### Version 1.0 (Future)
- [ ] Full plugin ecosystem
- [ ] GUI interface option
- [ ] Enterprise features

---

## 📋 Requirements

- Python 3.7 or higher
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))
- Internet connection (for API calls)

### Optional Dependencies
- `readline` (for command history in interactive mode)
- Terminal emulator with AppleScript support (macOS) or X11 (Linux)

---

## 🔧 Installation

### Quick Install (Recommended)

```bash
git clone https://github.com/yashwankhede/Terminal_AI.git
cd Terminal_AI
chmod +x install.sh
./install.sh
```

The installation script will:
- Check for Python and pip
- Install required dependencies
- Prompt for your OpenAI API key
- Set up the `terminal-ai` command

### Manual Installation

```bash
# Clone repository
git clone https://github.com/yashwankhede/Terminal_AI.git
cd Terminal_AI

# Install dependencies
pip install -r requirements.txt

# Set API key
python terminal_ai_cli.py --set-api-key YOUR_API_KEY

# Make executable (optional)
chmod +x terminal_ai_cli.py
```

### Pip Installation (Coming Soon)

```bash
pip install terminal-ai
```

---

## 💻 Usage

### Basic Usage

```bash
# Single command
terminal-ai "list all files in current directory"

# Complex task
terminal-ai "create a backup of my Documents folder with timestamp"

# System information
terminal-ai "show me disk usage and running processes"
```

### Interactive Mode

```bash
terminal-ai --interactive
# or
terminal-ai -i
```

In interactive mode:
- Type your requests naturally
- Commands execute automatically
- Context is maintained across commands
- Use `help` for available commands
- Use `exit` or `quit` to leave

### Python API

```python
from terminal_ai import execute_commands_sequence, ask_ai_for_commands

# Get commands from AI
commands = ask_ai_for_commands(
    "list all Python files",
    api_key="your-api-key"
)

# Execute commands
execute_commands_sequence(commands, api_key="your-api-key")
```

---

## 🔒 Safety Features

- **Dangerous Command Detection**: Automatically flags potentially destructive commands
- **Confirmation Prompts**: Asks for confirmation before executing risky operations
- **Timeout Protection**: Commands timeout after 5 minutes by default
- **Secure Storage**: API keys stored with restricted permissions (600)
- **Error Handling**: Graceful error handling with clear error messages

---

## 🛠️ Configuration

Configuration is stored in `~/.terminal_ai/config.json` with secure permissions.

### Update API Key

```bash
terminal-ai --set-api-key YOUR_NEW_API_KEY
```

### Environment Variable

You can also set the API key via environment variable:

```bash
export OPENAI_API_KEY=your-api-key
```

### View Configuration

```bash
cat ~/.terminal_ai/config.json
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=terminal_ai

# Run specific test
pytest tests/test_core.py::test_execute_command
```

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Contribution Guide

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🐛 Issues & Discussions

- **Found a bug?** [Open an issue](https://github.com/yashwankhede/Terminal_AI/issues)
- **Have a question?** [Start a discussion](https://github.com/yashwankhede/Terminal_AI/discussions)
- **Want to contribute?** See [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 🙏 Acknowledgments

- Built with [OpenAI GPT](https://openai.com/)
- Inspired by the need for smarter terminal automation
- Thanks to all contributors and users!

---

## 📚 Documentation

- [Full Documentation](docs/)
- [API Reference](docs/api.md)
- [Examples](examples/)
- [Changelog](CHANGELOG.md)
- [Roadmap](ROADMAP.md)

---

**⭐ If Terminal_AI helped you, consider starring the repo!**

[![GitHub stars](https://img.shields.io/github/stars/yashwankhede/Terminal_AI.svg?style=social&label=Star)](https://github.com/yashwankhede/Terminal_AI)
