"""Configuration settings for RAG system using Pydantic."""

from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Paths
    project_root: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent,
        description="Project root directory"
    )

    @property
    def data_dir(self) -> Path:
        """Data directory path."""
        return self.project_root / "data"

    @property
    def database_dir(self) -> Path:
        """Database storage directory."""
        path = self.data_dir / "databases"
        path.mkdir(parents=True, exist_ok=True)
        return path

    # Ollama settings
    ollama_host: str = Field(
        default="http://localhost:11434",
        description="Ollama server host URL"
    )

    embedding_model: str = Field(
        default="mxbai-embed-large",
        description="Ollama embedding model to use"
    )

    embedding_dimension: int = Field(
        default=1024,
        description="Embedding vector dimension (mxbai-embed-large = 1024)"
    )

    # Indexing settings
    max_file_size_bytes: int = Field(
        default=1_000_000,
        description="Maximum file size to index (1MB default)"
    )

    batch_size: int = Field(
        default=10,
        description="Number of files to embed in a batch"
    )

    default_exclude_patterns: List[str] = Field(
        default=[
            "*.pyc",
            "__pycache__",
            ".git",
            ".gitignore",
            "node_modules",
            "*.log",
            "*.tmp",
            ".env",
            ".env.*",
            "venv",
            ".venv",
            "env",
            ".idea",
            ".vscode",
            "*.egg-info",
            "dist",
            "build",
            ".pytest_cache",
            ".tox",
            "*.db",
            "*.sqlite",
            "*.sqlite3",
        ],
        description="Default file patterns to exclude from indexing"
    )

    # Querying settings
    default_search_limit: int = Field(
        default=5,
        description="Default number of search results to return"
    )

    similarity_threshold: float = Field(
        default=0.001,
        description="Minimum similarity score threshold (0-1)"
    )

    # Skill settings
    @property
    def skill_output_dir(self) -> Path:
        """Claude Code skills directory."""
        path = Path.home() / ".claude" / "skills"
        path.mkdir(parents=True, exist_ok=True)
        return path

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )


# Global settings instance
settings = Settings()
