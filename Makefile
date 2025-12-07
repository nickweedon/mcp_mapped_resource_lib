.PHONY: help install test lint typecheck all clean release

# Default target
help:
	@echo "Available targets:"
	@echo "  make install    - Install package with dev dependencies"
	@echo "  make lint       - Run ruff linting"
	@echo "  make typecheck  - Run mypy type checking"
	@echo "  make test       - Run pytest unit tests"
	@echo "  make all        - Run lint, typecheck, and test (recommended)"
	@echo "  make clean      - Remove build artifacts and cache files"
	@echo "  make release [VERSION=X.Y.Z] - Create a new release (auto-increments if no VERSION)"

# Install package with dev dependencies
install:
	pip install -e ".[dev]"

# Run linting with ruff
lint:
	@echo "Running ruff linting..."
	ruff check src/ tests/

# Run type checking with mypy
typecheck:
	@echo "Running mypy type checking..."
	mypy src/

# Run unit tests with pytest
test:
	@echo "Running pytest..."
	pytest tests/ -v --cov=mcp_mapped_resource_lib --cov-report=term-missing --cov-report=html

# Run all checks (lint + typecheck + test)
all: lint typecheck test
	@echo ""
	@echo "✓ All checks passed!"

# Clean build artifacts and cache
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Create a new release (VERSION is optional - auto-increments patch if not provided)
release:
	@if [ -z "$(VERSION)" ]; then \
		echo "Auto-incrementing patch version..."; \
		./release.sh; \
	else \
		echo "Creating release $(VERSION)..."; \
		./release.sh $(VERSION); \
	fi
