# Configuration file for the Sphinx documentation builder.

import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Project information
project = 'Terminal_AI'
copyright = '2025, Terminal_AI Contributors'
author = 'Terminal_AI Contributors'
release = '0.1.0'
version = '0.1.0'

# Extensions
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
]

# Templates
templates_path = ['_templates']

# Exclude patterns
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# HTML output options
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Autodoc options
autodoc_mock_imports = ['openai']

