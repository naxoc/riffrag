#!/usr/bin/env python3
"""Generate Claude Code skills for RAG databases."""

import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from src.storage.lancedb_store import LanceDBStore

logger = logging.getLogger(__name__)
console = Console()
app = typer.Typer(help="Generate Claude Code skills for RAG databases")


def generate_skill(
    database_name: str,
    skill_name: Optional[str] = None,
    description: Optional[str] = None,
    output_dir: Optional[Path] = None,
) -> Path:
    """Generate a Claude Code skill for a RAG database.

    Args:
        database_name: Name of the RAG database
        skill_name: Name for the skill (default: {database_name}-rag)
        description: Skill description
        output_dir: Output directory (default: ~/.claude/skills)

    Returns:
        Path to created skill directory
    """
    # Set defaults
    skill_name = skill_name or f"{database_name}-rag"
    description = description or f"Query the {database_name} codebase using RAG"
    output_dir = output_dir or settings.skill_output_dir

    # Get absolute path to this project
    project_root = Path(__file__).parent.parent.absolute()

    # Create skill directory
    skill_dir = output_dir / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Create skill.md file
    skill_file = skill_dir / "skill.md"

    skill_content = f'''---
name: {skill_name}
description: {description}
---

Query the {database_name} codebase to find relevant code and documentation.

**Usage:**
- Ask natural language questions about the codebase
- Find specific implementations or patterns
- Get context about how features work

**Examples:**
- "How is authentication implemented?"
- "Where is the database configured?"
- "Find all API endpoints"

**Note:** This skill uses RAG (Retrieval-Augmented Generation) to search {database_name}.
Results include the most relevant files with similarity scores.

---

```python
#!/usr/bin/env python3
"""Claude Code skill for querying {database_name} RAG."""

import sys
from pathlib import Path

# Add RAG project to path
sys.path.insert(0, str(Path("{project_root}")))

from src.querying.query_engine import QueryEngine

def main():
    # Get query from command line arguments
    query = " ".join(sys.argv[1:])

    if not query:
        print("Error: Please provide a query")
        print("Usage: @{skill_name} <your question>")
        sys.exit(1)

    try:
        # Query the RAG database
        engine = QueryEngine(database_name="{database_name}")

        results = engine.query(
            query_text=query,
            limit=5,
            format_style="claude"
        )

        if not results:
            print(f"No results found for: {{query}}")
            print("\\nTry:")
            print("  • A more general query")
            print("  • Different keywords")
            sys.exit(0)

        # Format results for Claude
        output = engine.format_results(results, style="claude")
        print(output)

    except Exception as e:
        print(f"Error querying RAG: {{e}}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```
'''

    # Write skill file
    with open(skill_file, 'w', encoding='utf-8') as f:
        f.write(skill_content)

    logger.info(f"Created skill at: {skill_file}")
    return skill_dir


@app.command()
def create(
    database: str = typer.Option(
        ...,
        "--database",
        "-d",
        help="Name of the RAG database",
    ),
    skill_name: Optional[str] = typer.Option(
        None,
        "--skill-name",
        "-n",
        help="Name for the skill (default: {database}-rag)",
    ),
    description: Optional[str] = typer.Option(
        None,
        "--description",
        help="Skill description",
    ),
    list_databases: bool = typer.Option(
        False,
        "--list",
        help="List all available databases",
    ),
):
    """Generate a Claude Code skill for a RAG database.

    Example:
        python -m skills.skill_generator create \\
            --database my-project \\
            --skill-name my-project-rag \\
            --description "Query my project codebase"
    """
    # Handle list databases
    if list_databases:
        store = LanceDBStore()
        databases = store.list_tables()

        if not databases:
            console.print("[yellow]No databases found[/yellow]")
            console.print("\nCreate a database first:")
            console.print("  python scripts/index_codebase.py --path /path/to/code --name my-project")
            return

        console.print("[bold cyan]Available Databases:[/bold cyan]\n")
        for db in databases:
            stats = store.get_stats(db)
            console.print(f"  • [cyan]{db}[/cyan]")
            if stats:
                console.print(f"    Files: {stats['total_files']}")
        return

    # Verify database exists
    store = LanceDBStore()
    if not store.table_exists(database):
        console.print(f"[bold red]Error:[/bold red] Database '{database}' does not exist")
        console.print(f"\nAvailable databases: {store.list_tables()}")
        sys.exit(1)

    # Generate skill
    try:
        console.print(f"[cyan]Generating Claude Code skill for database:[/cyan] {database}")

        skill_dir = generate_skill(
            database_name=database,
            skill_name=skill_name,
            description=description,
        )

        console.print(f"\n[green]✓[/green] Skill created at: [bold]{skill_dir}[/bold]")
        console.print(f"\n[bold cyan]Usage in Claude Code:[/bold cyan]")

        skill_name = skill_name or f"{database}-rag"
        console.print(f"  @{skill_name} How does authentication work?")
        console.print(f"  @{skill_name} Find all API endpoints")
        console.print(f"  @{skill_name} Where is the database configured?")

        console.print(f"\n[yellow]Note:[/yellow] Restart Claude Code if it's already running to load the new skill")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        logger.exception("Skill generation failed")
        sys.exit(1)


if __name__ == "__main__":
    app()
