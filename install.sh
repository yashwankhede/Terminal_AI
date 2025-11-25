#!/bin/bash

# Terminal AI Installation Script
# This script installs the Terminal AI tool and requests necessary permissions

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INSTALL_DIR="/usr/local/bin"
BINARY_NAME="terminal-ai"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Terminal AI Installation Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if running as root (for system-wide installation)
if [ "$EUID" -ne 0 ]; then 
    echo -e "${YELLOW}Note: Not running as root. Some operations may require sudo.${NC}"
    SUDO_CMD="sudo"
else
    SUDO_CMD=""
fi

# Check Python installation
echo -e "${BLUE}[1/6]${NC} Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed. Please install Python 3 first.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✓${NC} Found: $PYTHON_VERSION"

# Check pip installation
echo -e "${BLUE}[2/6]${NC} Checking pip installation..."
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}pip3 not found. Installing pip...${NC}"
    $SUDO_CMD python3 -m ensurepip --upgrade
fi
echo -e "${GREEN}✓${NC} pip3 is available"

# Install Python dependencies
echo -e "${BLUE}[3/6]${NC} Installing Python dependencies..."

# Check if openai is already installed
if python3 -c "import openai" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} OpenAI package already installed"
else
    # Try installing with --user flag first (recommended)
    if pip3 install --user openai 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Dependencies installed"
    # If that fails, try with --break-system-packages (for externally managed environments)
    elif pip3 install --user --break-system-packages openai 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Dependencies installed (with --break-system-packages)"
    else
        # Show the actual error and provide guidance
        echo -e "${YELLOW}Standard installation failed. Attempting with --break-system-packages...${NC}"
        pip3 install --user --break-system-packages openai
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓${NC} Dependencies installed"
        else
            echo -e "${RED}Error: Failed to install dependencies.${NC}"
            echo ""
            echo -e "${YELLOW}Please install manually using one of these methods:${NC}"
            echo "  1. pip3 install --user openai"
            echo "  2. pip3 install --user --break-system-packages openai"
            echo ""
            echo -e "${YELLOW}Or use a virtual environment:${NC}"
            echo "  python3 -m venv venv"
            echo "  source venv/bin/activate"
            echo "  pip install openai"
            exit 1
        fi
    fi
fi

# Request OpenAI API key
echo ""
echo -e "${BLUE}[4/6]${NC} OpenAI API Key Configuration"
echo -e "${YELLOW}Please enter your OpenAI API key:${NC}"
echo -e "${YELLOW}(You can get one from https://platform.openai.com/api-keys)${NC}"
read -sp "API Key: " API_KEY
echo ""

if [ -z "$API_KEY" ]; then
    echo -e "${RED}Error: API key cannot be empty.${NC}"
    echo -e "${YELLOW}You can set it later using: terminal-ai --set-api-key YOUR_KEY${NC}"
else
    # Set API key using the tool itself
    if [ -f "$SCRIPT_DIR/terminal_ai_cli.py" ]; then
        python3 "$SCRIPT_DIR/terminal_ai_cli.py" --set-api-key "$API_KEY"
    else
        python3 -m terminal_ai.cli --set-api-key "$API_KEY"
    fi
    echo -e "${GREEN}✓${NC} API key configured"
fi

# Make the script executable
echo -e "${BLUE}[5/6]${NC} Setting up executable..."
if [ -f "$SCRIPT_DIR/terminal_ai_cli.py" ]; then
    chmod +x "$SCRIPT_DIR/terminal_ai_cli.py"
    EXECUTABLE="$SCRIPT_DIR/terminal_ai_cli.py"
else
    # Fallback to module execution
    EXECUTABLE="python3 -m terminal_ai.cli"
fi

# Create symlink or copy to /usr/local/bin
echo -e "${BLUE}[6/6]${NC} Installing to system PATH..."
if [ -w "$INSTALL_DIR" ]; then
    INSTALL_CMD="ln -sf"
    INSTALL_TARGET="$INSTALL_DIR/$BINARY_NAME"
else
    INSTALL_CMD="$SUDO_CMD ln -sf"
    INSTALL_TARGET="$INSTALL_DIR/$BINARY_NAME"
fi

# Remove old installation if exists
if [ -L "$INSTALL_TARGET" ] || [ -f "$INSTALL_TARGET" ]; then
    $SUDO_CMD rm -f "$INSTALL_TARGET"
fi

# Create symlink or wrapper script
if [ -f "$SCRIPT_DIR/terminal_ai_cli.py" ]; then
    # Create symlink to the CLI script
    $INSTALL_CMD "$SCRIPT_DIR/terminal_ai_cli.py" "$INSTALL_TARGET"
else
    # Create a wrapper script for module execution
    cat > "$INSTALL_TARGET" << 'EOF'
#!/bin/bash
python3 -m terminal_ai.cli "$@"
EOF
    $SUDO_CMD chmod +x "$INSTALL_TARGET"
fi

# Make sure it's executable
$SUDO_CMD chmod +x "$INSTALL_TARGET"

echo -e "${GREEN}✓${NC} Installed to $INSTALL_TARGET"

# Request permissions (macOS specific)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo ""
    echo -e "${BLUE}Permission Setup (macOS)${NC}"
    echo -e "${YELLOW}This tool needs the following permissions:${NC}"
    echo "  • Full Disk Access (for file operations)"
    echo "  • Terminal Access (for command execution)"
    echo ""
    echo -e "${YELLOW}To grant permissions:${NC}"
    echo "  1. Open System Settings > Privacy & Security"
    echo "  2. Add Terminal (or your terminal app) to:"
    echo "     - Full Disk Access"
    echo "     - Automation (if needed)"
    echo ""
    echo -e "${YELLOW}For sudo/root access, you may need to:${NC}"
    echo "  • Add your user to the sudoers file (if not already)"
    echo "  • Configure passwordless sudo for specific commands (optional)"
    echo ""
    read -p "Press Enter to continue..."
fi

# Linux specific permissions
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo ""
    echo -e "${BLUE}Permission Setup (Linux)${NC}"
    echo -e "${YELLOW}This tool may need:${NC}"
    echo "  • sudo access for system operations"
    echo "  • Execution permissions (already granted)"
    echo ""
    echo -e "${YELLOW}To test sudo access, you can run:${NC}"
    echo "  sudo -v"
    echo ""
    read -p "Press Enter to continue..."
fi

# Test installation
echo ""
echo -e "${BLUE}Testing installation...${NC}"
if command -v "$BINARY_NAME" &> /dev/null || command -v terminal-ai &> /dev/null; then
    echo -e "${GREEN}✓${NC} Installation successful!"
    echo ""
    echo -e "${GREEN}Terminal AI is now installed!${NC}"
    echo ""
    echo -e "${BLUE}Usage examples:${NC}"
    echo "  terminal-ai 'list all files in current directory'"
    echo "  terminal-ai --interactive"
    echo "  terminal-ai -i"
    echo ""
    echo -e "${YELLOW}Note:${NC} Commands execute automatically in interactive mode."
    echo -e "${YELLOW}      Use with caution and review commands before execution.${NC}"
else
    echo -e "${YELLOW}Warning:${NC} Installation completed but command not found in PATH."
    echo -e "${YELLOW}You may need to restart your terminal or run:${NC}"
    echo "  source ~/.zshrc  # or ~/.bashrc"
fi

echo ""
echo -e "${GREEN}Installation complete!${NC}"

