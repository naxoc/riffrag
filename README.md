# RiffRag: A local RAG builder with a Claude Code skills creator

A RAG system for indexing and querying codebases using LanceDB and Ollama embeddings. Designed for integration with Claude Code skills to save tokens and provide better context when working with multiple codebases. Main focus is **WordPress and PHP/JavaScript** codebases.

**Installation is dead simple:** Just paste a few commands and you're done. No Python knowledge needed, no virtual environments to manage, no config files to edit. It just works.

**RiffRag** helps you understand codebases by creating searchable vector embeddings locally, with tight Claude Code integration for token-efficient development.

## What RiffRag Is Good For

RiffRag currently works best with **small-to-medium sized codebases** (up to ~500 files). It's optimized for:

- ✅ It might even be a bit **faster** than waiting for Claude Code to `read`, `glob`, `grep`, and `ls` its way through code.
- ✅ **Saving tokens** that Claude Code or other paid services would be gobbling up instead.
- ✅ **Individual WordPress plugins or themes** (not all of WordPress Core)
- ✅ **Drupal modules** or other CMS extensions
- ✅ **PHP projects** (Laravel apps, custom projects, etc.)
- ✅ **JavaScript/Node.js projects**
- ✅ **Focused libraries and tools** 

**Current Implementation:** RiffRag uses line-based chunking that splits files into manageable sections while preserving context. This works well for most projects and handles large files intelligently.

**Coming Soon:** Function-level chunking for PHP and JavaScript (see [ROADMAP.md](ROADMAP.md)) will provide even more precise results by extracting individual functions and classes.

## Why RiffRag?

There are probably a million RAG tools out there, but I found that they all were hard to get started with, required cloud services, or were too expensive to use regularly. I also just wanted to play with this to understand better. It's probably a bit opinionated and suited to my own workflow (WordPress development, PHP/JS projects), but maybe it helps you too!

**Trade-offs:** This is optimized for simplicity and speed over precision. It uses line-based chunking which works well for most projects. If you need production-grade function-level search with AST parsing, check out the [roadmap](ROADMAP.md) for upcoming improvements.

**Full disclosure:** This project was built entirely using Claude Code. I'm not a Python developer, so if you find issues, please open an issue or PR!

## Features

- **Smart chunking**: Automatic line-based chunking that handles files of any size
- **Local embeddings**: Use Ollama's mxbai-embed-large for private, cost-free embeddings
- **Vector search**: Fast similarity search with LanceDB
- **Smart filtering**: Respects .gitignore and common exclusion patterns
- **Multiple codebases**: Separate database per codebase for clean isolation
- **Claude Code skills**: Generate skills for token-efficient querying
- **Rich CLI**: A rather pretty command-line interface with progress tracking

## Requirements

- **macOS** with Homebrew (Linux probably works with some tweaking)
- **Python 3.9+** (already on your Mac - you don't need to do anything)
- That's it! Everything else installs automatically (see Installation below)

## Installation

### Do you have Homebrew installed?

If not, get it here: [brew.sh](https://brew.sh) - it's a package manager for macOS that makes installing stuff easy.

### One-command installation

Once you have Homebrew, just paste these commands and you're done:

```bash
# Install dependencies (just, gum, and ollama)
brew install just gum ollama

# Clone and setup RiffRag
git clone https://github.com/naxoc/riffrag.git
cd riffrag
just setup

# Pull the embedding model
ollama pull mxbai-embed-large

# Verify everything is working
just check
```

That's it! You're ready to go. You don't need to know Python, activate virtual environments, or anything like that. The `just` commands handle everything for you.

### Quick Start Example

Here's how to index your first codebase and create a Claude Code skill:

```bash
# Index a codebase (e.g., a WordPress plugin)
just index ~/Sites/my-plugin my-plugin

# Create a Claude Code skill for it
just skill my-plugin

# Query it directly (or just let Claude Code use it automatically)
just query my-plugin "How does authentication work?"
```

Done! Now restart Claude Code and you can use `@my-plugin-rag` in your conversations.

Note that the indexer respects `.gitignore` so all that is ignored by git is ignored when indexing too. If you need to ignore more things, then pass for example `--exclude "*.doc,dist-dir/**"`  to exclude .doc files and everything a dir called dist-dir.

### Configuration (Optional)

RiffRag works out of the box, but you can customize settings by creating a `.env` file:

```bash
cp .env.example .env
```

Key settings you might want to change:
- `DEFAULT_SEARCH_LIMIT` - Number of results to return (default: 5)
- `BATCH_SIZE` - Number of chunks to embed at once (default: 10)

**Note on embedding models:** While the code supports configurable models via `EMBEDDING_MODEL`, only `mxbai-embed-large` has been tested and verified to work. Other models (including code-specific variants) have been found to produce unusable embeddings in practice.

See `.env.example` for all available options.

## Usage

All commands use `just` - it's simple and hides all the Python complexity. Just type `just` to see all available commands.

#### Index a Codebase
```bash
just index /path/to/codebase my-project

# With options:
just index /path/to/codebase my-project --exclude "*.log,*.tmp,somedir/*" --max-file-size 1000000 --batch-size 10
```

**Options:**
- `--exclude`: Additional file patterns to exclude (comma-separated, e.g., "*.log,*.tmp,somedir/*,*.jpg") Note that it respects `.gitignore` so all that is ignored by git is ignored when indexing too.
- `--max-file-size`: Maximum file size in bytes (default: 1000000 = 1MB)
- `--batch-size`: Number of files to embed at once (default: 10)

#### Update a RAG (Delete and Re-index)
```bash
just update my-project /path/to/codebase

# With options:
just update my-project /path/to/codebase --exclude "*.pyc,*.log" --batch-size 20
```
This automatically deletes the old database and re-indexes from scratch.

#### Query a Database
```bash
just query my-project "How does authentication work?"

# With options:
just query my-project "your question" --limit 10 --format machine --min-similarity 0.001
```

**Options:**
- `--limit`: Number of results to return (default: 5)
- `--format`: Output format - 'human' (colorful) or 'machine' (structured, default: 'human')
- `--min-similarity`: Minimum similarity threshold (default: 0.001)
- `--extension`: Filter by file extension (e.g., '.py')

#### Generate Claude Code Skill
This creates a Claude Code skill that you can use with `@skill-name` in your Claude Code sessions.

```bash
just skill my-project
```

This will interactively prompt you (using `gum`) for:
- **Skill name** (default: `my-project-rag`)
- **Codebase name(s)** - Human-friendly name(s) for the codebase (can use comma-separated nicknames like "newspack,plugin")
- **Description** - Optional description to help Claude understand what the codebase is

After creation, restart Claude Code if you have it running, and then use it in Claude Code:
```
@my-project-rag How does authentication work?
@my-project-rag Find all API endpoints
```

Or just let Claude Code decide when to query the RAGs. It's pretty good at figuring that out itself.

#### Other Useful Commands
```bash
just list              # List all databases with stats
just delete my-project # Delete a specific database
just clean             # Delete all databases
just stats my-project  # Show database statistics
just check             # Verify Ollama is ready
just test              # Quick test (index this project)
```

## Architecture

```
src/
├── embeddings/     # Ollama embedding generation
├── storage/        # LanceDB vector storage
├── chunking/       # File reading and chunking
├── indexing/       # Indexing pipeline
├── querying/       # Query engine
└── utils/          # File filtering and utilities

scripts/            # CLI tools
skills/             # Claude Code skill generator
config/             # Configuration management
data/databases/     # LanceDB storage (gitignored)
```

## Configuration

Configuration is managed in `config/settings.py`. You can override settings with environment variables:

```bash
export OLLAMA_HOST="http://localhost:11434"
export EMBEDDING_MODEL="mxbai-embed-large"
export MAX_FILE_SIZE_BYTES=1000000
```

Or create a `.env` file in the project root.

## How It Works

1. **Indexing**:
   - Walk the codebase directory
   - Filter files (respect .gitignore, skip binaries)
   - Split files into manageable chunks with line-number tracking
   - Generate 1024-dim embeddings with Ollama (mxbai-embed-large)
   - Store in LanceDB with metadata

2. **Querying**:
   - Convert query to embedding
   - Search LanceDB for similar vectors
   - Rank by cosine similarity
   - Return top K results with file paths

3. **Claude Code Integration**:
   - Generate skill that calls query engine
   - Format results for Claude consumption
   - Save tokens by retrieving only relevant code

## Performance

- **Indexing speed**: 2-5 files/second (GPU-dependent)
- **Query speed**: <1 second per query
- **Storage**: ~5KB per file in database
- **Example**: 1000 files ≈ 3-8 minutes indexing, ~5MB database

## Troubleshooting

**Ollama connection error**:
- Ensure Ollama is running: `ollama serve`
- Check model is available: `ollama list`
- Pull model if needed: `ollama pull mxbai-embed-large`

**Model issues**:
- Only `mxbai-embed-large` is supported and tested
- Code-specific models (like nomic-embed-code) have been found to produce degenerate embeddings
- Stick with mxbai for reliable results

**Encoding errors**:
- The system auto-detects file encoding
- Binary files are automatically skipped
- Check logs for specific problem files

**Large files truncated**:
- Adjust `--max-file-size` to allow larger files
- Very large files (>1MB) may be skipped by default

## Development

RiffRag uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.

**Install dev dependencies:**
```bash
pip install -r requirements-dev.txt
```

**Lint and format:**
```bash
just lint      # Check code quality
just format    # Auto-format code
just fix       # Fix issues + format
```

Configuration is in `.ruff.toml`.

## Advanced: Using Python Scripts Directly

If you can't use `just` for some reason, you can call the Python scripts directly:

**Index a codebase:**
```bash
./venv/bin/python3 scripts/index_codebase.py \
  --path /path/to/your/codebase \
  --name my-project \
  --exclude "*.log,*.tmp" \
  --max-file-size 1000000
```

**Query a database:**
```bash
./venv/bin/python3 scripts/query_rag.py \
  --database my-project \
  --query "How is authentication implemented?" \
  --limit 5
```

**Generate a skill:**
```bash
./venv/bin/python3 -m skills.skill_generator create \
  --database my-project \
  --skill-name my-project-rag \
  --codebase-names "my-project,plugin" \
  --description "Query the my-project codebase"
```

## License

MIT License
