#!/bin/bash

SOURCES="liblk tests examples"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${YELLOW}$1${NC}"
}

main() {
    print_status "Formatting Python code..."
    ruff format $SOURCES

    print_status "Checking and fixing code..."
    ruff check $SOURCES --fix

    print_status "Running type checks..."
    mypy $SOURCES

    print_status "Running tests..."
    python3 -m pytest tests/

    echo -e "${GREEN}Code formatting and checks complete!${NC}"
}

main
