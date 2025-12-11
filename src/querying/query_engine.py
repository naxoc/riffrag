"""Query engine for searching RAG databases."""

import logging
from typing import Optional

from config.settings import settings
from src.embeddings.ollama_embedder import OllamaEmbedder
from src.storage.lancedb_store import LanceDBStore

logger = logging.getLogger(__name__)


class QueryEngine:
    """Engine for querying RAG databases."""

    def __init__(
        self,
        database_name: str,
        embedder: Optional[OllamaEmbedder] = None,
        store: Optional[LanceDBStore] = None,
    ):
        """Initialize query engine.

        Args:
            database_name: Name of the codebase database
            embedder: Optional embedder instance (creates new if None)
            store: Optional store instance (creates new if None)
        """
        self.database_name = database_name
        self.embedder = embedder or OllamaEmbedder()
        self.store = store or LanceDBStore()

        # Verify database exists
        if not self.store.table_exists(database_name):
            raise ValueError(f"Database '{database_name}' does not exist")

        logger.info(f"Initialized QueryEngine for database: {database_name}")

    def query(
        self,
        query_text: str,
        limit: int = None,
        min_similarity: Optional[float] = None,
        extension_filter: Optional[str] = None,
        format_style: str = "human",
    ) -> list[dict]:
        """Query the RAG database.

        Args:
            query_text: Natural language query
            limit: Maximum number of results (default from settings)
            min_similarity: Minimum similarity threshold (0-1)
            extension_filter: Filter by file extension (e.g., '.py')
            format_style: Output format ('human' or 'machine')

        Returns:
            List of matching results
        """
        if not query_text or not query_text.strip():
            logger.warning("Empty query provided")
            return []

        limit = limit if limit is not None else settings.default_search_limit
        min_similarity = (
            min_similarity if min_similarity is not None else settings.similarity_threshold
        )

        logger.info(f"Querying: '{query_text}' (limit={limit})")

        # Step 1: Generate query embedding
        # Add prefix if configured (required for nomic-embed-text, not needed for mxbai-embed-large)
        if settings.use_embedding_prefixes:
            query_to_embed = f"search_query: {query_text}"
        else:
            query_to_embed = query_text

        try:
            query_embedding = self.embedder.embed(query_to_embed)
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            raise

        # Step 2: Build filters
        filters = None
        if extension_filter:
            filters = f"extension = '{extension_filter}'"

        # Step 3: Search database
        try:
            results = self.store.search(
                codebase_name=self.database_name,
                query_embedding=query_embedding,
                limit=limit,
                filters=filters,
            )
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

        # Step 4: Filter by similarity threshold
        filtered_results = [r for r in results if r["similarity"] >= min_similarity]

        logger.info(
            f"Found {len(filtered_results)} results above similarity threshold {min_similarity}"
        )

        return filtered_results

    def format_results(
        self,
        results: list[dict],
        style: str = "human",
        max_content_length: Optional[int] = None,
    ) -> str:
        """Format query results for display.

        Args:
            results: List of result dictionaries
            style: Format style ('human' or 'machine')
            max_content_length: Maximum content length to display

        Returns:
            Formatted string
        """
        if not results:
            return "No results found."

        if style == "machine":
            return self._format_for_machine(results, max_content_length)
        else:
            return self._format_human(results, max_content_length)

    def _format_human(self, results: list[dict], max_length: Optional[int]) -> str:
        """Format results in human-readable style.

        Args:
            results: List of result dictionaries
            max_length: Maximum content length

        Returns:
            Formatted string
        """
        output = []
        output.append(f"Found {len(results)} relevant files:\n")

        # First, list all files with metadata
        for idx, result in enumerate(results, 1):
            # Show file path with line numbers if chunked
            total_chunks = result.get("total_chunks") or 1
            start_line = result.get("start_line") or 1
            end_line = result.get("end_line") or 1
            chunk_index = result.get("chunk_index") or 0

            if total_chunks > 1:
                file_display = f"{result['file_path']} (lines {start_line}-{end_line}, chunk {chunk_index + 1}/{total_chunks})"
            elif start_line and end_line:
                file_display = f"{result['file_path']} (lines {start_line}-{end_line})"
            else:
                file_display = result["file_path"]

            output.append(f"{idx}. {file_display}")
            output.append(
                f"   Similarity: {result['similarity']:.3f} | Size: {result['size_bytes']} bytes"
            )

        output.append("\n" + "=" * 60 + "\n")

        # Then show full content for each file
        for idx, result in enumerate(results, 1):
            # Show file path with line numbers
            total_chunks = result.get("total_chunks") or 1
            start_line = result.get("start_line") or 1
            end_line = result.get("end_line") or 1
            chunk_index = result.get("chunk_index") or 0

            if total_chunks > 1:
                header = f"## {idx}. {result['file_path']} (lines {start_line}-{end_line}, chunk {chunk_index + 1}/{total_chunks})\n"
            elif start_line and end_line:
                header = f"## {idx}. {result['file_path']} (lines {start_line}-{end_line})\n"
            else:
                header = f"## {idx}. {result['file_path']}\n"

            output.append(header)

            content = result["content"]
            if max_length and len(content) > max_length:
                content = content[:max_length] + "\n... (truncated)"

            output.append(content)
            output.append("\n" + "-" * 60 + "\n")

        return "\n".join(output)

    def _format_for_machine(self, results: list[dict], max_length: Optional[int]) -> str:
        """Format results optimized for machine consumption.

        Args:
            results: List of result dictionaries
            max_length: Maximum content length

        Returns:
            Formatted string
        """
        output = []
        output.append(f"Found {len(results)} relevant files:\n")

        for idx, result in enumerate(results, 1):
            # Show file path with line numbers
            total_chunks = result.get("total_chunks") or 1
            start_line = result.get("start_line") or 1
            end_line = result.get("end_line") or 1
            chunk_index = result.get("chunk_index") or 0

            if total_chunks > 1:
                header = f"\n## {idx}. {result['file_path']} (lines {start_line}-{end_line}, chunk {chunk_index + 1}/{total_chunks})"
            elif start_line and end_line:
                header = f"\n## {idx}. {result['file_path']} (lines {start_line}-{end_line})"
            else:
                header = f"\n## {idx}. {result['file_path']}"

            output.append(header)
            output.append(
                f"**Relevance:** {result['similarity']:.2%} | **Type:** {result['extension']}"
            )
            output.append("\n```")

            content = result["content"]
            if max_length and len(content) > max_length:
                content = content[:max_length] + "\n... (truncated)"

            output.append(content)
            output.append("```\n")

        return "\n".join(output)


def query_database(
    database_name: str,
    query_text: str,
    limit: int = None,
    format_style: str = "human",
) -> str:
    """Query a RAG database (convenience function).

    Args:
        database_name: Name of the codebase database
        query_text: Natural language query
        limit: Maximum number of results
        format_style: Output format style

    Returns:
        Formatted results string
    """
    engine = QueryEngine(database_name)
    results = engine.query(query_text, limit=limit, format_style=format_style)
    return engine.format_results(results, style=format_style)
