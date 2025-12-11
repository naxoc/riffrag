"""LanceDB storage layer for vector embeddings."""

import hashlib
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import lancedb
import pyarrow as pa

from config.settings import settings

logger = logging.getLogger(__name__)


class LanceDBStore:
    """LanceDB vector database operations."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize LanceDB store.

        Args:
            db_path: Path to LanceDB storage directory (default from settings)
        """
        self.db_path = db_path or settings.database_dir
        self.db = lancedb.connect(str(self.db_path))
        logger.info(f"Connected to LanceDB at {self.db_path}")

    @staticmethod
    def sanitize_name(name: str) -> str:
        """Sanitize database name to be filesystem-safe.

        Args:
            name: Raw name

        Returns:
            Sanitized name safe for filesystem
        """
        # Replace spaces and special chars with underscores
        sanitized = re.sub(r"[^\w\-]", "_", name.lower())
        # Remove multiple underscores
        sanitized = re.sub(r"_+", "_", sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip("_")
        return sanitized

    def _get_table_name(self, codebase_name: str) -> str:
        """Get table name for a codebase.

        Args:
            codebase_name: Name of the codebase

        Returns:
            Sanitized table name
        """
        return f"{self.sanitize_name(codebase_name)}_rag"

    @staticmethod
    def _generate_id(codebase_name: str, file_path: str) -> str:
        """Generate unique ID for a chunk.

        Args:
            codebase_name: Name of the codebase
            file_path: Relative file path

        Returns:
            Unique ID string
        """
        content = f"{codebase_name}:{file_path}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def create_table(self, codebase_name: str, embedding_dim: int = None) -> str:
        """Create a new table for a codebase.

        Args:
            codebase_name: Name of the codebase
            embedding_dim: Dimension of embedding vectors

        Returns:
            Table name created
        """
        table_name = self._get_table_name(codebase_name)
        dim = embedding_dim or settings.embedding_dimension

        # Check if table already exists
        if table_name in self.db.table_names():
            logger.info(f"Table '{table_name}' already exists")
            return table_name

        # Create schema
        schema = pa.schema(
            [
                pa.field("id", pa.string()),
                pa.field("codebase_name", pa.string()),
                pa.field("file_path", pa.string()),
                pa.field("absolute_path", pa.string()),
                pa.field("content", pa.string()),
                pa.field("extension", pa.string()),
                pa.field("size_bytes", pa.int64()),
                pa.field("modified_at", pa.string()),
                pa.field("language", pa.string()),
                pa.field("start_line", pa.int32()),
                pa.field("end_line", pa.int32()),
                pa.field("chunk_index", pa.int32()),
                pa.field("total_chunks", pa.int32()),
                pa.field("vector", pa.list_(pa.float32(), dim)),
            ]
        )

        # Create empty table
        self.db.create_table(table_name, schema=schema)
        logger.info(f"Created table '{table_name}' with dimension {dim}")

        return table_name

    def insert_chunks(self, codebase_name: str, chunks: list[dict[str, Any]]) -> int:
        """Insert chunks into the database.

        Args:
            codebase_name: Name of the codebase
            chunks: List of chunk dictionaries with 'embedding' field

        Returns:
            Number of chunks inserted
        """
        if not chunks:
            logger.warning("No chunks to insert")
            return 0

        table_name = self._get_table_name(codebase_name)

        # Ensure table exists
        if table_name not in self.db.table_names():
            self.create_table(codebase_name)

        table = self.db.open_table(table_name)

        # Prepare data for insertion
        data = []
        for chunk in chunks:
            # Generate ID if not present
            chunk_id = chunk.get("id") or self._generate_id(codebase_name, chunk["file_path"])

            data.append(
                {
                    "id": chunk_id,
                    "codebase_name": codebase_name,
                    "file_path": chunk["file_path"],
                    "absolute_path": chunk.get("absolute_path", ""),
                    "content": chunk.get("content", ""),
                    "extension": chunk.get("extension", ""),
                    "size_bytes": chunk.get("size_bytes", 0),
                    "modified_at": chunk.get("modified_at", datetime.now().isoformat()),
                    "language": chunk.get("language", ""),
                    "start_line": chunk.get("start_line", 1),
                    "end_line": chunk.get("end_line", 1),
                    "chunk_index": chunk.get("chunk_index", 0),
                    "total_chunks": chunk.get("total_chunks", 1),
                    "vector": chunk["embedding"],
                }
            )

        # Insert data
        table.add(data)
        logger.info(f"Inserted {len(data)} chunks into '{table_name}'")

        return len(data)

    def search(
        self,
        codebase_name: str,
        query_embedding: list[float],
        limit: int = None,
        filters: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Search for similar chunks.

        Args:
            codebase_name: Name of the codebase
            query_embedding: Query embedding vector
            limit: Maximum number of results
            filters: Optional SQL-like filter string

        Returns:
            List of matching chunks with similarity scores
        """
        table_name = self._get_table_name(codebase_name)
        limit = limit or settings.default_search_limit

        if table_name not in self.db.table_names():
            logger.error(f"Table '{table_name}' does not exist")
            return []

        table = self.db.open_table(table_name)

        # Perform vector search
        search_query = table.search(query_embedding).limit(limit)

        if filters:
            search_query = search_query.where(filters)

        results = search_query.to_list()

        # Convert results to dictionaries
        output = []
        for result in results:
            # LanceDB returns distance, convert to similarity score
            distance = result.get("_distance", 0)
            similarity = 1 / (1 + distance)  # Convert distance to similarity

            output.append(
                {
                    "id": result["id"],
                    "file_path": result["file_path"],
                    "absolute_path": result.get("absolute_path", ""),
                    "content": result["content"],
                    "extension": result["extension"],
                    "size_bytes": result["size_bytes"],
                    "modified_at": result.get("modified_at", ""),
                    "language": result.get("language", ""),
                    "start_line": result.get("start_line", 1),
                    "end_line": result.get("end_line", 1),
                    "chunk_index": result.get("chunk_index", 0),
                    "total_chunks": result.get("total_chunks", 1),
                    "similarity": similarity,
                    "distance": distance,
                }
            )

        return output

    def delete_table(self, codebase_name: str) -> bool:
        """Delete a codebase table.

        Args:
            codebase_name: Name of the codebase

        Returns:
            True if deleted, False if table didn't exist
        """
        table_name = self._get_table_name(codebase_name)

        if table_name not in self.db.table_names():
            logger.warning(f"Table '{table_name}' does not exist")
            return False

        self.db.drop_table(table_name)
        logger.info(f"Deleted table '{table_name}'")
        return True

    def list_tables(self) -> list[str]:
        """List all codebase tables.

        Returns:
            List of codebase names (without _rag suffix)
        """
        tables = self.db.table_names()
        # Remove _rag suffix to get codebase names
        codebases = [t.replace("_rag", "") for t in tables if t.endswith("_rag")]
        return codebases

    def get_stats(self, codebase_name: str) -> Optional[dict[str, Any]]:
        """Get statistics for a codebase.

        Args:
            codebase_name: Name of the codebase

        Returns:
            Dictionary with statistics or None if table doesn't exist
        """
        table_name = self._get_table_name(codebase_name)

        if table_name not in self.db.table_names():
            logger.warning(f"Table '{table_name}' does not exist")
            return None

        table = self.db.open_table(table_name)
        count = table.count_rows()

        # Get file extension distribution
        df = table.to_pandas()
        extension_counts = df["extension"].value_counts().to_dict()

        return {
            "codebase_name": codebase_name,
            "table_name": table_name,
            "total_files": count,
            "extension_distribution": extension_counts,
        }

    def table_exists(self, codebase_name: str) -> bool:
        """Check if table exists for codebase.

        Args:
            codebase_name: Name of the codebase

        Returns:
            True if table exists, False otherwise
        """
        table_name = self._get_table_name(codebase_name)
        return table_name in self.db.table_names()
