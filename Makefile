# MCP Audit Makefile

.PHONY: lint typecheck test build clean format all

# Default target
all: lint typecheck test

# Lint with ruff
lint:
	ruff check src/ tests/

# Type check only src/ with mypy strict
typecheck:
	mypy src/mcp_audit

# Run tests with pytest
test:
	pytest tests/ --tb=short -q

# Build the package (optional - requires pip install build)
build:
	@command -v python3 -c "import build" >/dev/null 2>&1 && python3 -m build || echo "Skipping build (python build module not installed)"

# Format code with black
format:
	black src/ tests/

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info/ __pycache__/ .pytest_cache/ .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Install development dependencies
install:
	pip install -e ".[dev]"
