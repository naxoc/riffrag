# RiffRag - Just Recipes
# https://github.com/casey/just
# Run 'just' to see all available recipes
set dotenv-load

# Default recipe (show help)
default:
    @just --list

# Setup: Create venv and install dependencies. Only needs to be run once.
[group('Getting started')]
setup:
    python3 -m venv venv
    ./venv/bin/pip3 install -r requirements.txt
    @echo "✓ Setup complete! Run 'source venv/bin/activate' to activate the venv"
    @echo ""
    @echo "For development (includes linting): pip install -r requirements-dev.txt"

# Index a codebase: just index /path/to/code my-project [--exclude "*.log" --max-file-size 1000000 --batch-size 10]
[group('RAG management')]
index PATH NAME *ARGS:
    ./venv/bin/python3 scripts/index_codebase.py --path "{{PATH}}" --name "{{NAME}}" {{ARGS}}

# Update (delete and re-index): just update my-project /path/to/code [--exclude "*.pyc" --batch-size 20]
[group('RAG management')]
update NAME PATH *ARGS:
    @echo "Deleting existing database: {{NAME}}"
    rm -rf data/databases/{{NAME}}_rag.lance
    @echo "Re-indexing from scratch..."
    ./venv/bin/python3 scripts/index_codebase.py --path "{{PATH}}" --name "{{NAME}}" {{ARGS}}

# Query a database: just query my-project "your question" [--limit 10 --format human|machine --min-similarity 0.001]
[group('Using the RAGs')]
query NAME QUERY *ARGS:
    ./venv/bin/python3 scripts/query_rag.py --database "{{NAME}}" --query "{{QUERY}}" {{ARGS}}

# Generate Claude Code skill (interactive): just skill my-project
[group('Using the RAGs')]
skill NAME:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "Creating Claude Code skill for database: {{NAME}}"
    echo ""
    SKILL_NAME=$(gum input --placeholder "Skill name" --value "{{NAME}}-rag" --prompt "Skill name: ")
    DESCRIPTION=$(gum input --placeholder "Description of this RAG" --value "Query the {{NAME}} codebase" --prompt "Description: " --width 100)
    echo ""
    echo "Creating skill '$SKILL_NAME'..."
    ./venv/bin/python3 -m skills.skill_generator \
        --database "{{NAME}}" \
        --skill-name "$SKILL_NAME" \
        --description "$DESCRIPTION"

# List all databases with stats (file counts and extensions)
[group('RAG management')]
list:
    ./venv/bin/python3 scripts/query_rag.py --list --database dummy --query dummy 2>/dev/null || true

# Delete a database: just delete my-project
[group('RAG management')]
delete NAME:
    @echo "Deleting database: {{NAME}}"
    rm -rf data/databases/{{NAME}}_rag.lance
    @echo "✓ Database deleted"

# Clean (delete) all RAG databases
[group('RAG management')]
clean:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "⚠️  This will DELETE ALL RAG databases!"
    echo ""
    if gum confirm "Are you sure you want to delete all databases?"; then
        echo "Deleting all databases..."
        rm -rf data/databases/*_rag.lance
        echo "✓ All databases deleted"
    else
        echo "Cancelled"
        exit 1
    fi

# Run a quick test (index this RAG project and query it). Useful for verifying the system is working
[group('Developer utilities')]
test:
    @echo "Testing by indexing this project..."
    just update riffrag-project .
    @echo "\nQuerying the test database..."
    just query riffrag-project "indexing pipeline" --limit 2

# Check Ollama has the embedding model installed
[group('Developer utilities')]
check:
    @echo "Checking that Ollama has the '$EMBEDDING_MODEL' pulled"
    @ollama list | grep $EMBEDDING_MODEL || (echo "❌ '$EMBEDDING_MODEL' not found. Run: ollama pull $EMBEDDING_MODEL" && exit 1)
    @echo "✓ Ollama is ready"

# Show database stats: just stats my-project
[group('RAG management')]
stats NAME:
    @./venv/bin/python3 -c "from src.storage.lancedb_store import LanceDBStore; store = LanceDBStore(); stats = store.get_stats('{{NAME}}'); print(f\"Database: {{NAME}}\nFiles: {stats['total_files']}\nExtensions: {stats['extension_distribution']}\") if stats else print('Database not found')"

# Lint Python code (checks quality without changes)
[group('Developer utilities')]
lint:
    @echo "Running Ruff linter..."
    ./venv/bin/ruff check .

# Format Python code (auto-formats with Ruff)
[group('Developer utilities')]
format:
    @echo "Formatting Python code..."
    ./venv/bin/ruff format .

# Fix auto-fixable issues and format code
[group('Developer utilities')]
fix:
    @echo "Fixing auto-fixable issues..."
    ./venv/bin/ruff check --fix .
    @echo "Running formatter..."
    ./venv/bin/ruff format .
