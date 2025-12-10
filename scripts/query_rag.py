#!/usr/bin/env python3
"""RiffRag - CLI script to query a RAG database."""

import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.panel import Panel

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from src.querying.query_engine import QueryEngine
from src.storage.lancedb_store import LanceDBStore

# Setup logging
logging.basicConfig(
    level=settings.log_level,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)

app = typer.Typer(help="Query a RAG database")
console = Console()


@app.command()
def main(
    database: Optional[str] = typer.Option(
        None,
        "--database",
        "-d",
        help="Name of the RAG database to query",
    ),
    query: Optional[str] = typer.Option(
        None,
        "--query",
        "-q",
        help="Natural language query",
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-l",
        help=f"Maximum number of results (default: {settings.default_search_limit})",
    ),
    format_style: str = typer.Option(
        "plain",
        "--format",
        "-f",
        help="Output format: 'plain' or 'claude'",
    ),
    extension: Optional[str] = typer.Option(
        None,
        "--extension",
        "-e",
        help="Filter by file extension (e.g., '.py')",
    ),
    min_similarity: Optional[float] = typer.Option(
        None,
        "--min-similarity",
        help=f"Minimum similarity threshold 0-1 (default: {settings.similarity_threshold})",
    ),
    list_databases: bool = typer.Option(
        False,
        "--list",
        help="List all available databases",
    ),
):
    """Query a RAG database with natural language.

    Example:
        python scripts/query_rag.py \\
            --database my-project \\
            --query "How is authentication implemented?" \\
            --limit 5 \\
            --format claude
    """
    # Handle list databases
    if list_databases:
        store = LanceDBStore()
        databases = store.list_tables()

        if not databases:
            console.print("[yellow]No databases found[/yellow]")
            return

        console.print(Panel.fit(
            "[bold cyan]Available Databases[/bold cyan]\n\n" +
            "\n".join(f"  • {db}" for db in databases),
            border_style="cyan"
        ))

        # Show stats for each database
        console.print("\n[bold]Database Statistics:[/bold]\n")
        for db in databases:
            stats = store.get_stats(db)
            if stats:
                console.print(f"[cyan]{db}[/cyan]:")
                console.print(f"  Files: {stats['total_files']}")
                console.print(f"  Extensions: {list(stats['extension_distribution'].keys())}")
                console.print()

        return

    # Validate required arguments
    if not database:
        console.print("[bold red]Error:[/bold red] --database is required")
        console.print("Use --list to see available databases")
        sys.exit(1)

    if not query:
        console.print("[bold red]Error:[/bold red] --query is required")
        sys.exit(1)

    # Validate database exists
    store = LanceDBStore()
    if not store.table_exists(database):
        console.print(f"[bold red]Error:[/bold red] Database '{database}' does not exist")
        console.print(f"\nAvailable databases: {store.list_tables()}")
        console.print(f"\nRun with --list to see all databases")
        sys.exit(1)

    # Display query info
    console.print(Panel.fit(
        f"[bold cyan]Querying RAG Database[/bold cyan]\n\n"
        f"[yellow]Database:[/yellow] {database}\n"
        f"[yellow]Query:[/yellow] {query}\n"
        f"[yellow]Limit:[/yellow] {limit or settings.default_search_limit}\n"
        f"[yellow]Format:[/yellow] {format_style}",
        border_style="cyan"
    ))

    # Run query
    try:
        engine = QueryEngine(database)

        results = engine.query(
            query_text=query,
            limit=limit,
            min_similarity=min_similarity,
            extension_filter=extension,
            format_style=format_style,
        )

        if not results:
            console.print("\n[yellow]No results found matching your query.[/yellow]")
            console.print("\nTips:")
            console.print("  • Try a more general query")
            console.print("  • Lower the --min-similarity threshold")
            console.print("  • Check if the codebase was indexed correctly")
            return

        # Format and display results
        formatted = engine.format_results(results, style=format_style)

        console.print("\n")
        if format_style == "claude":
            # Render as markdown for claude format
            console.print(Markdown(formatted))
        else:
            console.print(formatted)

        # Show summary
        console.print(f"\n[green]✓[/green] Found {len(results)} relevant files")

    except KeyboardInterrupt:
        console.print("\n[yellow]Query interrupted by user[/yellow]")
        sys.exit(1)

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        logger.exception("Query failed")
        sys.exit(1)


if __name__ == "__main__":
    app()
