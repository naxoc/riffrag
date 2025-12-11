"""Main indexing pipeline for codebases."""

import logging
import time
from pathlib import Path
from typing import Optional

from tqdm import tqdm

from config.settings import settings
from src.chunking.file_chunker import FileChunker
from src.embeddings.ollama_embedder import OllamaEmbedder
from src.storage.lancedb_store import LanceDBStore
from src.utils.file_utils import FileFilter, count_files_by_extension

logger = logging.getLogger(__name__)


class CodebaseIndexer:
    """Index a codebase into a RAG database."""

    def __init__(
        self,
        codebase_path: Path,
        codebase_name: str,
        additional_exclude: Optional[list[str]] = None,
        max_file_size: Optional[int] = None,
        batch_size: Optional[int] = None,
    ):
        """Initialize codebase indexer.

        Args:
            codebase_path: Path to codebase directory
            codebase_name: Name for this RAG database
            additional_exclude: Additional file patterns to exclude
            max_file_size: Maximum file size in bytes
            batch_size: Number of files to process in a batch
        """
        self.codebase_path = Path(codebase_path)
        self.codebase_name = codebase_name
        self.additional_exclude = additional_exclude or []
        self.batch_size = batch_size or settings.batch_size

        # Initialize components
        self.file_filter = FileFilter(self.codebase_path, self.additional_exclude)
        self.embedder = OllamaEmbedder()  # Create embedder first to get context_length
        self.file_chunker = FileChunker(
            max_file_size, max_chunk_tokens=self.embedder.context_length
        )
        self.store = LanceDBStore()

        # Statistics
        self.stats = {
            "total_files_found": 0,
            "files_processed": 0,
            "files_skipped": 0,
            "files_failed": 0,
            "chunks_created": 0,
            "start_time": None,
            "end_time": None,
        }

    def index(self, show_progress: bool = True) -> dict:
        """Run the indexing pipeline.

        Args:
            show_progress: Whether to show progress bars

        Returns:
            Dictionary with indexing statistics
        """
        logger.info(f"Starting indexing of {self.codebase_path}")
        logger.info(f"Database name: {self.codebase_name}")

        self.stats["start_time"] = time.time()

        # Step 1: Discover files
        logger.info("Step 1: Discovering files...")
        files = self.file_filter.walk_files(show_progress=show_progress)
        self.stats["total_files_found"] = len(files)

        if not files:
            logger.warning("No files found to index!")
            return self.stats

        # Show file distribution
        ext_counts = count_files_by_extension(files)
        logger.info(f"File distribution: {ext_counts}")

        # Step 2: Create table
        logger.info("Step 2: Creating/verifying database table...")
        self.store.create_table(self.codebase_name, embedding_dim=self.embedder.dimension)

        # Step 3: Process files in batches
        logger.info(f"Step 3: Processing files in batches of {self.batch_size}...")
        self._process_files_in_batches(files, show_progress)

        # Step 4: Finalize
        self.stats["end_time"] = time.time()
        duration = self.stats["end_time"] - self.stats["start_time"]

        logger.info("=" * 60)
        logger.info("Indexing complete!")
        logger.info(f"Total files found: {self.stats['total_files_found']}")
        logger.info(f"Files processed: {self.stats['files_processed']}")
        logger.info(f"Files skipped: {self.stats['files_skipped']}")
        logger.info(f"Files failed: {self.stats['files_failed']}")
        logger.info(f"Chunks created: {self.stats['chunks_created']}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Speed: {self.stats['files_processed'] / duration:.2f} files/sec")
        logger.info("=" * 60)

        return self.stats

    def _process_files_in_batches(self, files: list[Path], show_progress: bool):
        """Process files in batches.

        Args:
            files: List of file paths to process
            show_progress: Whether to show progress bar
        """
        total_batches = (len(files) + self.batch_size - 1) // self.batch_size

        # Create progress bar if requested
        if show_progress:
            progress = tqdm(total=len(files), desc="Indexing files", unit="file")
        else:
            progress = None

        for batch_idx in range(total_batches):
            start_idx = batch_idx * self.batch_size
            end_idx = min(start_idx + self.batch_size, len(files))
            batch_files = files[start_idx:end_idx]

            logger.debug(f"Processing batch {batch_idx + 1}/{total_batches}")

            # Process batch
            self._process_batch(batch_files)

            # Update progress
            if progress:
                progress.update(len(batch_files))

        if progress:
            progress.close()

    def _process_batch(self, batch_files: list[Path]):
        """Process a batch of files.

        Args:
            batch_files: List of file paths in this batch
        """
        # Step 1: Read files and create chunks
        chunks = []
        for file_path in batch_files:
            file_chunks = self.file_chunker.chunk_file(file_path, self.codebase_root)

            if not file_chunks:  # Empty list means file was skipped
                self.stats["files_skipped"] += 1
                logger.debug(f"Skipped: {file_path}")
                continue

            # Add all chunks from this file
            chunks.extend(file_chunks)
            self.stats["files_processed"] += 1

        if not chunks:
            logger.debug("No valid chunks in this batch")
            return

        # Step 2: Generate embeddings for batch
        try:
            # Log which files are in this batch
            batch_files = list(set(chunk["file_path"] for chunk in chunks))
            logger.debug(
                f"Processing batch of {len(chunks)} chunks from {len(batch_files)} files: {[str(f) for f in batch_files]}"
            )

            # Add prefix if configured (required for nomic-embed-text, not needed for mxbai-embed-large)
            if settings.use_embedding_prefixes:
                texts = [f"search_document: {chunk['content']}" for chunk in chunks]
            else:
                texts = [chunk["content"] for chunk in chunks]
            embeddings = self.embedder.embed_batch(texts, show_progress=False)

            # Add embeddings to chunks
            for chunk, embedding in zip(chunks, embeddings):
                chunk["embedding"] = embedding

        except Exception as e:
            logger.error(f"Failed to generate embeddings for batch: {e}")
            self.stats["files_failed"] += len(chunks)
            return

        # Step 3: Store in database
        try:
            count = self.store.insert_chunks(self.codebase_name, chunks)
            self.stats["chunks_created"] += count

        except Exception as e:
            logger.error(f"Failed to store chunks: {e}")
            self.stats["files_failed"] += len(chunks)

    @property
    def codebase_root(self) -> Path:
        """Get codebase root path."""
        return self.codebase_path


def index_codebase(
    codebase_path: str,
    name: str,
    additional_exclude: Optional[list[str]] = None,
    max_file_size: Optional[int] = None,
    batch_size: Optional[int] = None,
    show_progress: bool = True,
) -> dict:
    """Index a codebase (convenience function).

    Args:
        codebase_path: Path to codebase directory
        name: Name for this RAG database
        additional_exclude: Additional file patterns to exclude
        max_file_size: Maximum file size in bytes
        batch_size: Number of files to process in a batch
        show_progress: Whether to show progress bars

    Returns:
        Dictionary with indexing statistics
    """
    indexer = CodebaseIndexer(
        codebase_path=Path(codebase_path),
        codebase_name=name,
        additional_exclude=additional_exclude,
        max_file_size=max_file_size,
        batch_size=batch_size,
    )

    return indexer.index(show_progress=show_progress)
