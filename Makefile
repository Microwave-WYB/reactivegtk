.PHONY: sync install format lint typecheck test check all clean help

# Variables
UV := uv
SRC_DIR := src
DEMO_DIR := demos
PYTHON_FILES := $(SRC_DIR) $(DEMO_DIR)
PYTHON_VERSION := 3.10
FILE ?=

# Default target
help:
	@echo "Available targets:"
	@echo "  install    - Install dependencies with uv"
	@echo "  format     - Format code with ruff"
	@echo "  lint       - Lint code with ruff"
	@echo "  typecheck  - Type check with pyright"
	@echo "  doctest    - Run doctests (use FILE=path/to/file.py for specific file)"
	@echo "  pytest     - Run pytest (not implemented yet)"
	@echo "  test       - Run doctests and pytest"
	@echo "  check      - Run format, lint, and typecheck"
	@echo "  all        - sync, check, and test"
	@echo "  clean      - Clean up cache files"

# Sync dependencies
sync:
	$(UV) sync --python $(PYTHON_VERSION)

# Install dependencies (alias for sync)
install: sync

# Format code with ruff (includes import sorting)
format:
	$(UV) run ruff format $(SRC_DIR) $(DEMO_DIR)
	$(UV) run ruff check --select I --fix $(PYTHON_FILES)

# Lint code with ruff
lint:
	$(UV) run ruff check $(SRC_DIR) $(DEMO_DIR)

# Type checking with pyright
typecheck:
	$(UV) run pyright $(SRC_DIR) $(DEMO_DIR)

# Run doctests
doctest:
ifdef FILE
	@echo "Running doctests on $(FILE)..."
	@if grep -q ">>>" $(FILE); then \
		$(UV) run python -m doctest -v $(FILE); \
	else \
		echo "No doctests found in $(FILE)"; \
	fi
else
	@echo "Running doctests on all files..."
	@for file in $$(find $(SRC_DIR) $(DEMO_DIR) -name "*.py" -exec grep -l ">>>" {} \;); do \
		echo "Testing $$file"; \
		$(UV) run python -m doctest -v $$file; \
	done
endif

# Run pytest
pytest:
	@echo "pytest not implemented yet"

test: doctest pytest

# Run all checks
check: format lint typecheck

# Complete workflow
all: sync check test

# Cleanup cache files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf node_modules
