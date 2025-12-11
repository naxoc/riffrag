"""Ollama embedding generation client."""

import logging
import time
from typing import List, Union

import ollama
from ollama import Client

from config.settings import settings

logger = logging.getLogger(__name__)


class OllamaEmbedder:
    """Client for generating embeddings using Ollama."""

    def __init__(
        self,
        host: str = None,
        model: str = None,
    ):
        """Initialize Ollama embedder.

        Args:
            host: Ollama server URL (default from settings)
            model: Embedding model name (default from settings)
        """
        self.host = host or settings.ollama_host
        self.model = model or settings.embedding_model

        self.client = Client(host=self.host)

        # Auto-detect dimension from model if not explicitly set in env
        self.dimension = self._detect_dimension()

        logger.info(f"Initialized OllamaEmbedder with model={self.model}, dimension={self.dimension}, host={self.host}")

        # Verify model is available
        self._verify_model()

    def _detect_dimension(self) -> int:
        """Auto-detect embedding dimension from the model.

        Returns:
            Embedding dimension size

        Falls back to settings.embedding_dimension if detection fails.
        """
        # If explicitly set in env, use that (allows override)
        if hasattr(settings, '_env_file_loaded') or 'EMBEDDING_DIMENSION' in __import__('os').environ:
            return settings.embedding_dimension

        try:
            response = self.client.show(self.model)
            model_info = response.get('modelinfo', {})

            # Search for any key ending in '.embedding_length'
            # This works for any model architecture without hardcoding
            for key, value in model_info.items():
                if key.endswith('.embedding_length'):
                    logger.info(f"Auto-detected embedding dimension from '{key}': {value}")
                    return value

            logger.warning(f"Could not find embedding dimension in model info, using default: {settings.embedding_dimension}")
            return settings.embedding_dimension

        except Exception as e:
            logger.warning(f"Failed to auto-detect dimension: {e}, using default: {settings.embedding_dimension}")
            return settings.embedding_dimension

    def _verify_model(self) -> None:
        """Verify that the embedding model is available."""
        try:
            response = self.client.list()

            # Handle response - it might be a dict or an object
            if hasattr(response, 'models'):
                models = response.models
            elif isinstance(response, dict):
                models = response.get("models", [])
            else:
                # If we can't parse, just skip verification
                logger.debug("Could not parse Ollama model list, skipping verification")
                return

            # Extract model names
            available_models = []
            for m in models:
                if hasattr(m, 'model'):
                    available_models.append(m.model)
                elif isinstance(m, dict):
                    available_models.append(m.get("name", m.get("model", "")))

            if not any(self.model in m for m in available_models):
                logger.warning(
                    f"Model '{self.model}' not found in Ollama. Available models: {available_models}"
                )
                logger.warning(f"Please run: ollama pull {self.model}")

        except Exception as e:
            logger.warning(f"Could not verify Ollama model (this is OK if model exists): {e}")
            # Don't raise - model might still work

    def embed(self, text: str, retry_count: int = 3) -> List[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed
            retry_count: Number of retries on failure

        Returns:
            Embedding vector as list of floats

        Raises:
            RuntimeError: If embedding generation fails after retries
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding, returning zero vector")
            return [0.0] * self.dimension

        for attempt in range(retry_count):
            try:
                response = self.client.embeddings(
                    model=self.model,
                    prompt=text
                )
                embedding = response["embedding"]

                # Verify dimension
                if len(embedding) != self.dimension:
                    logger.warning(
                        f"Unexpected embedding dimension: {len(embedding)} (expected {self.dimension})"
                    )

                return embedding

            except Exception as e:
                logger.warning(f"Embedding attempt {attempt + 1}/{retry_count} failed: {e}")

                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to generate embedding after {retry_count} attempts")
                    raise RuntimeError(f"Embedding generation failed: {e}") from e

    def embed_batch(
        self,
        texts: List[str],
        show_progress: bool = False
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            show_progress: Whether to show progress bar

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        embeddings = []
        failed_indices = []

        iterator = texts
        if show_progress:
            try:
                from tqdm import tqdm
                iterator = tqdm(texts, desc="Generating embeddings")
            except ImportError:
                pass

        for idx, text in enumerate(iterator):
            try:
                embedding = self.embed(text)
                embeddings.append(embedding)
            except RuntimeError as e:
                logger.error(f"Failed to embed text at index {idx}: {e}")
                failed_indices.append(idx)
                # Add zero vector as placeholder
                embeddings.append([0.0] * self.dimension)

        if failed_indices:
            logger.warning(f"Failed to generate embeddings for {len(failed_indices)} texts")

        return embeddings

    def embed_with_metadata(
        self,
        items: List[dict],
        text_key: str = "content"
    ) -> List[dict]:
        """Generate embeddings for items with metadata.

        Args:
            items: List of dictionaries containing text and metadata
            text_key: Key in dict containing the text to embed

        Returns:
            List of items with 'embedding' field added
        """
        texts = [item.get(text_key, "") for item in items]
        embeddings = self.embed_batch(texts)

        results = []
        for item, embedding in zip(items, embeddings):
            result = item.copy()
            result["embedding"] = embedding
            results.append(result)

        return results

    def test_connection(self) -> bool:
        """Test connection to Ollama server.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.client.list()
            logger.info("Successfully connected to Ollama")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            return False
