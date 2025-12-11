# RiffRag - Just Recipes
# https://github.com/casey/just
# Run 'just' to see all available recipes

# Default recipe (show help)
default:
    @just --list

# Setup: Create venv and install dependencies
setup:
    python3 -m venv venv
    ./venv/bin/pip3 install -r requirements.txt
    @echo "✓ Setup complete! Run 'source venv/bin/activate' to activate the venv"

# Index a codebase into a RAG database
# Usage: just index /path/to/code my-project [--exclude "*.log,*.tmp" --max-file-size 1000000 --batch-size 10]
# Options:
#   --exclude: Patterns to exclude (comma-separated)
#   --max-file-size: Max file size in bytes (default: 1MB)
#   --batch-size: Files to embed at once (default: 10)
index PATH NAME *ARGS:
    ./venv/bin/python3 scripts/index_codebase.py --path "{{PATH}}" --name "{{NAME}}" {{ARGS}}

# Update a RAG database (delete and re-index from scratch)
# Usage: just update my-project /path/to/code [--exclude "*.pyc" --batch-size 20]
# This is the recommended way to refresh a database after code changes
update NAME PATH *ARGS:
    @echo "Deleting existing database: {{NAME}}"
    rm -rf data/databases/{{NAME}}_rag.lance
    @echo "Re-indexing from scratch..."
    ./venv/bin/python3 scripts/index_codebase.py --path "{{PATH}}" --name "{{NAME}}" {{ARGS}}

# Query a RAG database with natural language
# Usage: just query my-project "your question" [--limit 10 --format claude --min-similarity 0.001 --extension .py]
# Options:
#   --limit: Number of results (default: 5)
#   --format: 'plain' or 'claude' (default: plain)
#   --min-similarity: Threshold 0-1 (default: 0.001)
#   --extension: Filter by file type (e.g., '.py')
query NAME QUERY *ARGS:
    ./venv/bin/python3 scripts/query_rag.py --database "{{NAME}}" --query "{{QUERY}}" {{ARGS}}

# Generate a Claude Code skill for a RAG database (interactive with gum)
# Usage: just skill my-project
# Prompts for skill name and description interactively
# After generation, use in Claude Code: @my-project-rag your question here
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

# List all RAG databases with statistics
# Shows database names, file counts, and file extensions
list:
    ./venv/bin/python3 scripts/query_rag.py --list --database dummy --query dummy 2>/dev/null || true

# Delete a specific RAG database
# Usage: just delete my-project
delete NAME:
    @echo "Deleting database: {{NAME}}"
    rm -rf data/databases/{{NAME}}_rag.lance
    @echo "✓ Database deleted"

# Clean all RAG databases (careful!)
# Deletes all *_rag.lance directories in data/databases/
# Prompts for confirmation before deleting
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

# Run a quick test (index this RAG project and query it)
# Useful for verifying the system is working
test:
    @echo "Testing by indexing this project..."
    just update riffrag-project .
    @echo "\nQuerying the test database..."
    just query riffrag-project "indexing pipeline" --limit 2

# Check if Ollama is running and has the required model
# Verifies that mxbai-embed-large is available
check:
    @echo "Checking Ollama..."
    @ollama list | grep mxbai-embed-large || (echo "❌ mxbai-embed-large not found. Run: ollama pull mxbai-embed-large" && exit 1)
    @echo "✓ Ollama is ready"

# Install Python dependencies (without creating venv)
# Use 'just setup' instead if you want a venv
install:
    pip3 install -r requirements.txt

# Show detailed statistics for a database
# Usage: just stats my-project
# Displays file count and extension distribution
stats NAME:
    @./venv/bin/python3 -c "from src.storage.lancedb_store import LanceDBStore; store = LanceDBStore(); stats = store.get_stats('{{NAME}}'); print(f\"Database: {{NAME}}\nFiles: {stats['total_files']}\nExtensions: {stats['extension_distribution']}\") if stats else print('Database not found')"
