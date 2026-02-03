# RAG Facile development tasks

# Display available commands
default:
    @just --list

# Format code (write changes)
format:
    moon run tools:f i
# Check formatting without writing
format-check:
    moon run tools:format-check

# Run linter
lint:
    moon run tools:lint

# Run linter with auto-fix
lint-fix:
    moon run tools:lint-fix

# Run type checker
type-check:
    moon run tools:type-check

# Run all checks (format-check, lint, type-check)
check: format-check lint type-check
