"""File chunking module - reads files and extracts metadata."""

import logging
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import chardet

from config.settings import settings

logger = logging.getLogger(__name__)


class FileChunker:
    """Chunk files by reading entire files with metadata."""

    # Common code file extensions
    CODE_EXTENSIONS = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.c': 'c',
        '.cpp': 'cpp',
        '.cc': 'cpp',
        '.cxx': 'cpp',
        '.h': 'c',
        '.hpp': 'cpp',
        '.cs': 'csharp',
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.sh': 'shell',
        '.bash': 'shell',
        '.zsh': 'shell',
        '.fish': 'shell',
        '.r': 'r',
        '.R': 'r',
        '.m': 'matlab',
        '.sql': 'sql',
        '.html': 'html',
        '.htm': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.sass': 'sass',
        '.less': 'less',
        '.xml': 'xml',
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.toml': 'toml',
        '.ini': 'ini',
        '.cfg': 'ini',
        '.conf': 'conf',
        '.md': 'markdown',
        '.markdown': 'markdown',
        '.rst': 'restructuredtext',
        '.txt': 'text',
        '.vue': 'vue',
        '.svelte': 'svelte',
    }

    def __init__(self, max_file_size: int = None):
        """Initialize file chunker.

        Args:
            max_file_size: Maximum file size in bytes (default from settings)
        """
        self.max_file_size = max_file_size or settings.max_file_size_bytes

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
        if mime_type and mime_type.startswith('text/'):
            return False

        # Check by reading first few bytes
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                if not chunk:
                    return False

                # Check for null bytes (binary indicator)
                if b'\x00' in chunk:
                    return True

                # Try to decode as text
                try:
                    chunk.decode('utf-8')
                    return False
                except UnicodeDecodeError:
                    # Try to detect encoding
                    result = chardet.detect(chunk)
                    if result['encoding'] and result['confidence'] > 0.7:
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
            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)  # Read first 10KB
                result = chardet.detect(raw_data)
                encoding = result.get('encoding', 'utf-8')
                confidence = result.get('confidence', 0)

                if confidence < 0.7:
                    logger.debug(f"Low confidence ({confidence:.2f}) for encoding detection of {file_path}")

                return encoding or 'utf-8'

        except Exception as e:
            logger.warning(f"Error detecting encoding for {file_path}: {e}")
            return 'utf-8'

    def read_file(self, file_path: Path) -> Optional[str]:
        """Read file content with encoding detection.

        Args:
            file_path: Path to file

        Returns:
            File content as string, or None if unreadable
        """
        # Try UTF-8 first (most common)
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']

        # Add detected encoding to the front
        detected_encoding = self.detect_encoding(file_path)
        if detected_encoding not in encodings:
            encodings.insert(0, detected_encoding)

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
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
        return self.CODE_EXTENSIONS.get(ext, 'unknown')

    def chunk_file(
        self,
        file_path: Path,
        codebase_root: Path
    ) -> Optional[Dict]:
        """Create a chunk from a file.

        Args:
            file_path: Path to file
            codebase_root: Root directory of codebase (for relative paths)

        Returns:
            Chunk dictionary or None if file cannot be processed
        """
        # Check file size
        try:
            size = file_path.stat().st_size
            if size > self.max_file_size:
                logger.warning(
                    f"Skipping {file_path}: size {size} exceeds max {self.max_file_size}"
                )
                return None

            if size == 0:
                logger.debug(f"Skipping empty file: {file_path}")
                return None

        except Exception as e:
            logger.error(f"Error getting stats for {file_path}: {e}")
            return None

        # Check if binary
        if self.is_binary(file_path):
            logger.debug(f"Skipping binary file: {file_path}")
            return None

        # Read content
        content = self.read_file(file_path)
        if content is None:
            logger.warning(f"Failed to read file: {file_path}")
            return None

        # Get relative path
        try:
            relative_path = file_path.relative_to(codebase_root)
        except ValueError:
            relative_path = file_path

        # Get metadata
        stats = file_path.stat()
        modified_at = datetime.fromtimestamp(stats.st_mtime).isoformat()

        chunk = {
            "file_path": str(relative_path),
            "absolute_path": str(file_path.absolute()),
            "content": content,
            "extension": file_path.suffix,
            "size_bytes": size,
            "modified_at": modified_at,
            "language": self.get_language(file_path),
        }

        return chunk
