# RiffRag: A local RAG builder with a Claude Code skills creator

This project provides an easy way to build and query a Retrieval-Augmented Generation (RAG) system for your codebases using LanceDB and Ollama embeddings. It is optimized for use with Claude Code skills to help you save tokens and reduce costs when querying large codebases. **RiffRag** helps you understand large codebases by creating searchable vector embeddings locally, with tight Claude Code integration for token-efficient development.

## Why RiffRag?
There are probably a million RAG tools out there, but I found that they all were hard to get started with, required cloud services, or were too expensive to use regularly. I also just wanted to play with this to understand better. It's probably a bit opinionated and suited to my own workflow, but maybe it helps you too! I should add that this is all mostly written by Claude Code. I'm really not a Python dev, so if you find issues, please open an issue or PR!

## Features

- **File-level indexing**: Index entire files as semantic chunks
- **Local embeddings**: Use Ollama's mxbai-embed-large for private, cost-free embeddings
- **Vector search**: Fast similarity search with LanceDB
- **Smart filtering**: Respects .gitignore and common exclusion patterns
- **Multiple codebases**: Separate database per codebase for clean isolation
- **Claude Code skills**: Generate skills for token-efficient querying
- **Rich CLI**: A rather pretty command-line interface with progress tracking

## Requirements

- Python 3.9+ (I just used the vanilla version installed on macOS – I did nothing to set that up)
- [Ollama](https://ollama.ai/) installed and running. `brew install ollama` or download from their site.
- mxbai-embed-large model pulled: `ollama pull mxbai-embed-large`
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
```

4. Verify Ollama is running:
```bash
ollama list  # Should show mxbai-embed-large
```

## Usage
You can use `just` recipes for convenience or call the Python scripts directly.
### Using Just (Recommended)

If you have [just](https://github.com/casey/just) installed (and you really should because it's so darn convenient), you can use these convenient recipes:

#### Index a Codebase
```bash
just index /path/to/codebase my-project

# With options:
just index /path/to/codebase my-project --exclude "*.log,*.tmp,*.lock" --max-file-size 1000000 --batch-size 10
```

**Options:**
- `--exclude`: Additional file patterns to exclude (comma-separated, e.g., "*.log,*.tmp,*.lock,*.jpg")
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
just query my-project "your question" --limit 10 --format claude --min-similarity 0.001
```

**Options:**
- `--limit`: Number of results to return (default: 5)
- `--format`: Output format - 'plain' or 'claude' (default: 'plain')
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

After creation, use it in Claude Code:
```
@my-project-rag How does authentication work?
@my-project-rag Find all API endpoints
```

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
- `--format`: Output format: 'plain' or 'claude' (default: 'plain')

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
   - Read each file as a chunk
   - Generate 1024-dim embeddings with Ollama
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

**Encoding errors**:
- The system auto-detects file encoding
- Binary files are automatically skipped
- Check logs for specific problem files

**Large files truncated**:
- Adjust `--max-file-size` to allow larger files
- Very large files (>1MB) may be skipped by default

## License

MIT License
