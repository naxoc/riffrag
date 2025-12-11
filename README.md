# RiffRag: A local RAG builder with a Claude Code skills creator

A RAG system for indexing and querying  codebases using LanceDB and Ollama embeddings. Designed for integration with Claude Code skills to save tokens and provide better context when working with multiple codebases. Main focus is **WordPress and PHP/JavaScript** codebases. It's written in python, but you need not know any python at all (and likely do nothing in the way of setting up python on your Mac). Linux will probably work with some nudging.

Installation (on a Mac that is) is super easy and you don't need to touch settings or code if you don't want to. Just clone, install requirements (homebrew packages 'just' and 'gum'), and you're good to go.

**RiffRag** helps you understand codebases by creating searchable vector embeddings locally, with tight Claude Code integration for token-efficient development.

## What RiffRag Is Good For

RiffRag currently works best with **small-to-medium sized codebases** (up to ~500 files). It's optimized for:

- ✅ Projects with well-organized file structures.
- ✅ It might even be a bit faster than waiting for Claude Code to `read`, `glob`, `grep`, and `ls` its way through code.
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

- Python 3.9+ (I just used the vanilla version installed on macOS – I did nothing to set that up)
- [Ollama](https://ollama.ai/) installed and running: `brew install ollama` or download from their site
- Embedding model: `ollama pull mxbai-embed-large` (this is the only tested and working model)
- [Gum](https://github.com/charmbracelet/gum) for a more glamorous CLI experience: `brew install gum`
- [Just](https://github.com/casey/just) task runner. Like `make` but it doesn't suck: `brew install just`

## Installation

1. Clone this repository:
```bash
git clone https://github.com/naxoc/riffrag.git
cd riffrag
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip3 install -r requirements.txt

# Optional - for development (includes linting):
pip3 install -r requirements-dev.txt
```

4. Verify Ollama is running:
```bash
ollama list  # Should show nomic-embed-text
```

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
You can use `just` recipes for convenience or call the Python scripts directly if you are so inclined.
### Using Just (Recommended)

If you have [just](https://github.com/casey/just) installed (and you really should because it's so darn convenient), you can use these convenient recipes:

#### Index a Codebase
```bash
just index /path/to/codebase my-project

# With options:
just index /path/to/codebase my-project --exclude "*.log,*.tmp,somedir/*" --max-file-size 1000000 --batch-size 10
```

**Options:**
- `--exclude`: Additional file patterns to exclude (comma-separated, e.g., "*.log,*.tmp,somedir/*,*.jpg")
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
- **Description** (default: "Query the my-project codebase")

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

---

### Using Python Scripts Directly

If you prefer not to use `just`, you can call the scripts directly:

#### 1. Index a Codebase

Index a codebase to create a searchable RAG database:

```bash
python3 scripts/index_codebase.py \
  --path /path/to/your/codebase \
  --name my-project \
  --exclude "*.log,*.tmp,*.lock,*.jpg" \
  --max-file-size 1000000
```

Options:
- `--path`: Path to the codebase directory (required)
- `--name`: Name for this RAG database (required)
- `--exclude`: Additional file patterns to exclude (comma-separated)
- `--max-file-size`: Maximum file size in bytes (default: 1MB)

### 2. Query a RAG Database

Search your indexed codebase with natural language:

```bash
python3 scripts/query_rag.py \
  --database my-project \
  --query "How is authentication implemented?" \
  --limit 5
```

Options:
- `--database`: Name of the RAG database to query (required)
- `--query`: Natural language query (required)
- `--limit`: Number of results to return (default: 5)
- `--format`: Output format: 'human' (colorful) or 'machine' (structured, default: 'human')

### 3. Generate Claude Code Skill

Create a Claude Code skill for your RAG:

```bash
python3 -m skills.skill_generator create \
  --database my-project \
  --skill-name my-project-rag \
  --description "Query the my-project codebase"
```

Then use it in Claude Code:
```
@my-project-rag How does the authentication system work?
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

## License

MIT License
