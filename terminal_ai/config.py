"""
Configuration management for Terminal AI
Handles API keys, config files, and color output
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Configuration file path
CONFIG_DIR = Path.home() / ".terminal_ai"
CONFIG_FILE = CONFIG_DIR / "config.json"


# Colors for terminal output
class Colors:
    """ANSI color codes for terminal output"""

    BLUE = "\033[0;34m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    RED = "\033[0;31m"
    CYAN = "\033[0;36m"
    MAGENTA = "\033[0;35m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def load_config() -> Dict[str, Any]:
    """Load configuration from file"""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                logger.debug(f"Loaded config from {CONFIG_FILE}")
                return config
        logger.debug("No config file found, returning empty dict")
        return {}
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to file with secure permissions"""
    try:
        CONFIG_DIR.mkdir(exist_ok=True)
        # Set secure permissions (read/write for owner only)
        os.umask(0o077)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        os.chmod(CONFIG_FILE, 0o600)
        logger.debug(f"Saved config to {CONFIG_FILE}")
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        raise


def get_api_key() -> Optional[str]:
    """Get OpenAI API key from config or environment"""
    # Check environment variable first
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        logger.debug("Using API key from environment variable")
        return api_key

    # Fall back to config file
    config = load_config()
    api_key = config.get("api_key")
    if api_key:
        logger.debug("Using API key from config file")
    else:
        logger.warning("No API key found in config or environment")
    return api_key


def set_api_key(api_key: str) -> None:
    """Set OpenAI API key in config"""
    config = load_config()
    config["api_key"] = api_key
    save_config(config)
    logger.info("API key saved successfully")


def is_first_run() -> bool:
    """Check if this is the first run of Terminal AI"""
    first_run_file = CONFIG_DIR / ".first_run"
    if not first_run_file.exists():
        first_run_file.touch()
        return True
    return False
