"""File chunking module - reads files and extracts metadata."""

import logging
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Optional

import chardet

from config.settings import settings

logger = logging.getLogger(__name__)


class FileChunker:
    """Chunk files by reading entire files with metadata."""

    # Common code file extensions
    CODE_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".cs": "csharp",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".sh": "shell",
        ".bash": "shell",
        ".zsh": "shell",
        ".fish": "shell",
        ".r": "r",
        ".R": "r",
        ".m": "matlab",
        ".sql": "sql",
        ".html": "html",
        ".htm": "html",
        ".css": "css",
        ".scss": "scss",
        ".sass": "sass",
        ".less": "less",
        ".xml": "xml",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".ini": "ini",
        ".cfg": "ini",
        ".conf": "conf",
        ".md": "markdown",
        ".markdown": "markdown",
        ".rst": "restructuredtext",
        ".txt": "text",
        ".vue": "vue",
        ".svelte": "svelte",
    }

    def __init__(self, max_file_size: int = None, max_chunk_tokens: int = None):
        """Initialize file chunker.

        Args:
            max_file_size: Maximum file size in bytes (default from settings)
            max_chunk_tokens: Maximum tokens per chunk for embedding (default: auto-detect from model)
        """
        self.max_file_size = max_file_size or settings.max_file_size_bytes
        self.max_chunk_tokens = max_chunk_tokens  # Will be set by indexer if needed

    @staticmethod
    def is_binary(file_path: Path) -> bool:
        """Check if file is binary.

        Args:
            file_path: Path to file

        Returns:
            True if binary, False if text
        """
        # Check MIME type first
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type and mime_type.startswith("text/"):
            return False

        # Check by reading first few bytes
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(1024)
                if not chunk:
                    return False

                # Check for null bytes (binary indicator)
                if b"\x00" in chunk:
                    return True

                # Try to decode as text
                try:
                    chunk.decode("utf-8")
                    return False
                except UnicodeDecodeError:
                    # Try to detect encoding
                    result = chardet.detect(chunk)
                    if result["encoding"] and result["confidence"] > 0.7:
                        return False
                    return True

        except Exception as e:
            logger.warning(f"Error checking if {file_path} is binary: {e}")
            return True

    def detect_encoding(self, file_path: Path) -> str:
        """Detect file encoding.

        Args:
            file_path: Path to file

        Returns:
            Detected encoding string
        """
        try:
            with open(file_path, "rb") as f:
                raw_data = f.read(10000)  # Read first 10KB
                result = chardet.detect(raw_data)
                encoding = result.get("encoding", "utf-8")
                confidence = result.get("confidence", 0)

                if confidence < 0.7:
                    logger.debug(
                        f"Low confidence ({confidence:.2f}) for encoding detection of {file_path}"
                    )

                return encoding or "utf-8"

        except Exception as e:
            logger.warning(f"Error detecting encoding for {file_path}: {e}")
            return "utf-8"

    def read_file(self, file_path: Path) -> Optional[str]:
        """Read file content with encoding detection.

        Args:
            file_path: Path to file

        Returns:
            File content as string, or None if unreadable
        """
        # Try UTF-8 first (most common)
        encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]

        # Add detected encoding to the front
        detected_encoding = self.detect_encoding(file_path)
        if detected_encoding not in encodings:
            encodings.insert(0, detected_encoding)

        for encoding in encodings:
            try:
                with open(file_path, encoding=encoding) as f:
                    content = f.read()
                    logger.debug(f"Successfully read {file_path} with {encoding}")
                    return content

            except (UnicodeDecodeError, LookupError):
                continue
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
                return None

        logger.warning(f"Failed to read {file_path} with any encoding")
        return None

    def get_language(self, file_path: Path) -> str:
        """Detect programming language from file extension.

        Args:
            file_path: Path to file

        Returns:
            Language name or 'unknown'
        """
        ext = file_path.suffix.lower()
        return self.CODE_EXTENSIONS.get(ext, "unknown")

    def split_content_into_chunks(self, content: str, file_name: str = None) -> list[dict[str, any]]:
        """Split content into multiple chunks based on max_chunk_tokens.

        Args:
            content: File content to split
            file_name: Optional filename for logging

        Returns:
            List of dicts with 'content', 'start_line', 'end_line'
        """
        # If no chunking limit set, return entire content
        if not self.max_chunk_tokens:
            lines = content.split("\n")
            return [
                {
                    "content": content,
                    "start_line": 1,
                    "end_line": len(lines),
                    "chunk_index": 0,
                    "total_chunks": 1,
                }
            ]

        # Very conservative estimate for code: 1 token ≈ 1.5 characters
        # Use 70% of limit to leave safety margin
        max_chars = int(self.max_chunk_tokens * 1.5 * 0.7)

        # If content fits in one chunk, don't split
        if len(content) <= max_chars:
            lines = content.split("\n")
            return [
                {
                    "content": content,
                    "start_line": 1,
                    "end_line": len(lines),
                    "chunk_index": 0,
                    "total_chunks": 1,
                }
            ]

        # Split into chunks
        chunks = []
        lines = content.split("\n")
        current_chunk_lines = []
        current_chunk_chars = 0
        chunk_start_line = 1

        for line_num, line in enumerate(lines, 1):
            line_with_newline = line + "\n"
            line_chars = len(line_with_newline)

            # Handle extremely long lines by splitting them
            if line_chars > max_chars:
                file_info = f" in {file_name}" if file_name else ""
                logger.info(
                    f"Line {line_num}{file_info} is very long ({line_chars} chars), splitting into pieces"
                )

                # First, save any accumulated content
                if current_chunk_lines:
                    chunk_content = "".join(current_chunk_lines).strip()
                    chunks.append(
                        {
                            "content": chunk_content,
                            "start_line": chunk_start_line,
                            "end_line": line_num - 1,
                            "chunk_index": len(chunks),
                            "total_chunks": -1,
                        }
                    )
                    current_chunk_lines = []
                    current_chunk_chars = 0

                # Split the long line into max_chars pieces
                remaining = line_with_newline
                piece_count = 0
                while remaining:
                    # Take a chunk, try to break at a space if possible
                    if len(remaining) <= max_chars:
                        piece = remaining
                        remaining = ""
                    else:
                        # Try to find a good break point (space, comma, etc.)
                        piece = remaining[:max_chars]
                        # Look for last space in the piece to break cleanly
                        last_space = piece.rfind(" ")
                        if last_space > max_chars * 0.5:  # Only if space is in latter half
                            piece = remaining[:last_space + 1]
                            remaining = remaining[last_space + 1:]
                        else:
                            # No good break point, just split at max_chars
                            remaining = remaining[max_chars:]

                    # Add this piece as its own chunk
                    chunks.append(
                        {
                            "content": piece.strip(),
                            "start_line": line_num,
                            "end_line": line_num,
                            "chunk_index": len(chunks),
                            "total_chunks": -1,
                        }
                    )
                    piece_count += 1

                logger.debug(f"Split long line {line_num} into {piece_count} pieces")
                chunk_start_line = line_num + 1
                continue

            # If adding this line would exceed limit and we have content, save current chunk
            if current_chunk_chars + line_chars > max_chars and current_chunk_lines:
                chunk_content = "".join(current_chunk_lines).strip()
                chunks.append(
                    {
                        "content": chunk_content,
                        "start_line": chunk_start_line,
                        "end_line": line_num - 1,
                        "chunk_index": len(chunks),
                        "total_chunks": -1,  # Will update after
                    }
                )
                current_chunk_lines = []
                current_chunk_chars = 0
                chunk_start_line = line_num

            current_chunk_lines.append(line_with_newline)
            current_chunk_chars += line_chars

        # Add final chunk if any content remains
        if current_chunk_lines:
            chunk_content = "".join(current_chunk_lines).strip()
            chunks.append(
                {
                    "content": chunk_content,
                    "start_line": chunk_start_line,
                    "end_line": len(lines),
                    "chunk_index": len(chunks),
                    "total_chunks": -1,
                }
            )

        # Update total_chunks for all chunks
        total = len(chunks)
        for chunk in chunks:
            chunk["total_chunks"] = total

        logger.debug(f"Split content into {total} chunks ({len(content)} chars)")
        return chunks

    def chunk_file(self, file_path: Path, codebase_root: Path) -> list[dict]:
        """Create chunks from a file.

        Args:
            file_path: Path to file
            codebase_root: Root directory of codebase (for relative paths)

        Returns:
            List of chunk dictionaries (empty list if file cannot be processed)
        """
        # Check file size
        try:
            size = file_path.stat().st_size
            if size > self.max_file_size:
                logger.warning(
                    f"Skipping {file_path}: size {size} exceeds max {self.max_file_size}"
                )
                return []

            if size == 0:
                logger.debug(f"Skipping empty file: {file_path}")
                return []

        except Exception as e:
            logger.error(f"Error getting stats for {file_path}: {e}")
            return []

        # Check if binary
        if self.is_binary(file_path):
            logger.debug(f"Skipping binary file: {file_path}")
            return []

        # Read content
        content = self.read_file(file_path)
        if content is None:
            logger.warning(f"Failed to read file: {file_path}")
            return []

        # Get relative path
        try:
            relative_path = file_path.relative_to(codebase_root)
        except ValueError:
            relative_path = file_path

        # Get metadata
        stats = file_path.stat()
        modified_at = datetime.fromtimestamp(stats.st_mtime).isoformat()
        language = self.get_language(file_path)

        # Split content into chunks (may be single chunk if small enough)
        content_chunks = self.split_content_into_chunks(content, file_name=file_path.name)

        # Build full chunks with file metadata
        chunks = []
        for content_chunk in content_chunks:
            chunk = {
                "file_path": str(relative_path),
                "absolute_path": str(file_path.absolute()),
                "content": content_chunk["content"],
                "extension": file_path.suffix,
                "size_bytes": size,
                "modified_at": modified_at,
                "language": language,
                "start_line": content_chunk["start_line"],
                "end_line": content_chunk["end_line"],
                "chunk_index": content_chunk["chunk_index"],
                "total_chunks": content_chunk["total_chunks"],
            }
            chunks.append(chunk)

        if len(chunks) > 1:
            logger.info(f"Split {file_path.name} into {len(chunks)} chunks")

        return chunks
