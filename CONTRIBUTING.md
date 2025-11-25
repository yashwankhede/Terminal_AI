# Contributing to Terminal_AI

Thank you for your interest in contributing to Terminal_AI! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Respect different viewpoints and experiences

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/yashwankhede/Terminal_AI/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - System information (OS, Python version, etc.)
   - Error messages or logs

### Suggesting Features

1. Check [ROADMAP.md](ROADMAP.md) to see if it's already planned
2. Open a new issue with:
   - Clear description of the feature
   - Use cases and examples
   - Potential implementation approach (if you have ideas)

### Contributing Code

#### Setup Development Environment

```bash
# Fork and clone the repository
git clone https://github.com/your-username/Terminal_AI.git
cd Terminal_AI

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If available

# Install in development mode
pip install -e .
```

#### Development Workflow

1. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes**
   - Follow the code style (see below)
   - Add tests for new features
   - Update documentation as needed

3. **Run tests**
   ```bash
   pytest tests/
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "Add: description of your changes"
   ```
   
   Use conventional commit messages:
   - `Add:` for new features
   - `Fix:` for bug fixes
   - `Update:` for updates to existing features
   - `Refactor:` for code refactoring
   - `Docs:` for documentation changes

5. **Push and create Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```
   
   Then create a Pull Request on GitHub.

## Code Style

### Python Style Guide

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use type hints where possible
- Maximum line length: 100 characters
- Use descriptive variable and function names
- Add docstrings to all functions and classes

### Example

```python
def execute_command(
    command: str,
    timeout: int = 60,
    capture_output: bool = True
) -> Tuple[int, str]:
    """
    Execute a terminal command.
    
    Args:
        command: The command to execute
        timeout: Maximum execution time in seconds
        capture_output: Whether to capture command output
        
    Returns:
        Tuple of (exit_code, output)
    """
    # Implementation
    pass
```

## Testing

### Writing Tests

- Write tests for all new features
- Aim for >80% code coverage
- Use descriptive test names
- Test both success and failure cases

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=terminal_ai

# Run specific test file
pytest tests/test_core.py

# Run with verbose output
pytest -v
```

## Documentation

### Code Documentation

- Add docstrings to all functions and classes
- Use Google-style docstrings
- Include examples for complex functions

### User Documentation

- Update README.md for user-facing changes
- Add examples to examples/ directory
- Update CHANGELOG.md for significant changes

## Pull Request Process

1. **Ensure your PR:**
   - Has a clear title and description
   - References related issues
   - Includes tests
   - Updates documentation
   - Passes all CI checks

2. **Review Process:**
   - Maintainers will review your PR
   - Address any feedback or requested changes
   - Once approved, your PR will be merged

## Areas for Contribution

### Good First Issues

Look for issues labeled `good-first-issue` - these are great for newcomers!

### Priority Areas

- **Testing**: More test coverage
- **Documentation**: Examples, tutorials, API docs
- **Performance**: Optimizations and improvements
- **Features**: See ROADMAP.md for planned features
- **Bug Fixes**: Check Issues for reported bugs

## Questions?

- Open a [Discussion](https://github.com/yashwankhede/Terminal_AI/discussions)
- Check existing [Issues](https://github.com/yashwankhede/Terminal_AI/issues)
- Review [Documentation](docs/)

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Given credit in documentation

Thank you for contributing to Terminal_AI! 🎉

