#!/usr/bin/env python3
"""RiffRag - CLI script to index a codebase into RAG database."""

import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from src.indexing.indexer import index_codebase

# Setup logging
logging.basicConfig(
    level=settings.log_level, format="%(message)s", handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)

app = typer.Typer(help="Index a codebase into RAG database")
console = Console()


@app.command()
def main(
    path: Path = typer.Option(
        ...,
        "--path",
        "-p",
        help="Path to the codebase directory",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    name: str = typer.Option(
        ...,
        "--name",
        "-n",
        help="Name for this RAG database",
    ),
    exclude: Optional[str] = typer.Option(
        None,
        "--exclude",
        "-e",
        help="Additional file patterns to exclude (comma-separated)",
    ),
    max_file_size: Optional[int] = typer.Option(
        None,
        "--max-file-size",
        help=f"Maximum file size in bytes (default: {settings.max_file_size_bytes})",
    ),
    batch_size: Optional[int] = typer.Option(
        None,
        "--batch-size",
        help=f"Number of files to process in a batch (default: {settings.batch_size})",
    ),
    no_progress: bool = typer.Option(
        False,
        "--no-progress",
        help="Disable progress bars",
    ),
):
    """Index a codebase into a RAG database.

    Example:
        python scripts/index_codebase.py \\
            --path /path/to/codebase \\
            --name my-project \\
            --exclude "*.log,*.tmp"
    """
    # Get actual embedding dimension (auto-detected or manual)
    from src.embeddings.ollama_embedder import OllamaEmbedder

    temp_embedder = OllamaEmbedder()
    actual_dimension = temp_embedder.dimension

    console.print(
        Panel.fit(
            f"[bold cyan]Indexing Codebase[/bold cyan]\n\n"
            f"[yellow]Path:[/yellow] {path}\n"
            f"[yellow]Name:[/yellow] {name}\n"
            f"[yellow]Database:[/yellow] {settings.database_dir / (name + '_rag')}\n"
            f"[yellow]Model:[/yellow] {settings.embedding_model}\n"
            f"[yellow]Dimensions:[/yellow] {actual_dimension}\n"
            f"[yellow]Batch size:[/yellow] {batch_size or settings.batch_size}",
            border_style="cyan",
        )
    )

    # Parse exclude patterns
    additional_exclude = None
    if exclude:
        additional_exclude = [p.strip() for p in exclude.split(",")]
        console.print(f"[yellow]Additional exclude patterns:[/yellow] {additional_exclude}")

    # Run indexing
    try:
        stats = index_codebase(
            codebase_path=str(path),
            name=name,
            additional_exclude=additional_exclude,
            max_file_size=max_file_size,
            batch_size=batch_size,
            show_progress=not no_progress,
        )

        # Display results
        duration = stats["end_time"] - stats["start_time"]
        speed = stats["files_processed"] / duration if duration > 0 else 0

        console.print("\n")
        console.print(
            Panel.fit(
                f"[bold green]Indexing Complete![/bold green]\n\n"
                f"[yellow]Total files found:[/yellow] {stats['total_files_found']}\n"
                f"[yellow]Files processed:[/yellow] {stats['files_processed']}\n"
                f"[yellow]Files skipped:[/yellow] {stats['files_skipped']}\n"
                f"[yellow]Files failed:[/yellow] {stats['files_failed']}\n"
                f"[yellow]Chunks created:[/yellow] {stats['chunks_created']}\n"
                f"[yellow]Duration:[/yellow] {duration:.2f} seconds\n"
                f"[yellow]Speed:[/yellow] {speed:.2f} files/sec",
                border_style="green",
            )
        )

        console.print(
            f"\n[green]✓[/green] Database saved to: {settings.database_dir / (name + '_rag')}"
        )
        console.print("\n[cyan]Next steps:[/cyan]")
        console.print(
            f'  1. Query the RAG: [bold]just query {name} "your question"[/bold]'
        )
        console.print(
            f"  2. Generate skill: [bold]just skill {name}[/bold]"
        )

    except KeyboardInterrupt:
        console.print("\n[yellow]Indexing interrupted by user[/yellow]")
        sys.exit(1)

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        logger.exception("Indexing failed")
        sys.exit(1)


if __name__ == "__main__":
    app()
