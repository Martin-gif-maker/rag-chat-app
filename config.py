"""RagChat -- centralised application settings.

All configuration is loaded from environment variables and the .env file.
Import the shared ``settings`` singleton anywhere you need a config value:

    from config import settings
    key = settings.groq_api_key
"""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings for RagChat.

    Values are read from environment variables (case-insensitive) and from
    a ``.env`` file in the project root, with environment variables taking
    priority.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Required -- the app will not start without this.
    # ------------------------------------------------------------------
    groq_api_key: str = Field(..., description="Groq API key for the LLM.")

    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------
    groq_model: str = Field(
        default="llama-3.3-70b-versatile",
        description="Groq model used for answering questions.",
    )

    # ------------------------------------------------------------------
    # RAG / retrieval settings
    # ------------------------------------------------------------------
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="SentenceTransformers model used for text embeddings.",
    )
    chroma_collection: str = Field(
        default="documents",
        description="ChromaDB collection name.",
    )
    chunk_size: int = Field(
        default=600,
        description="Maximum characters per text chunk.",
    )
    chunk_overlap: int = Field(
        default=80,
        description="Character overlap between consecutive chunks.",
    )
    retrieval_top_k: int = Field(
        default=5,
        description="Number of chunks to retrieve per query.",
    )

    # ------------------------------------------------------------------
    # Server
    # ------------------------------------------------------------------
    host: str = Field(default="127.0.0.1", description="Bind address for the dev server.")
    port: int = Field(default=8000, description="Port for the dev server.")
    reload: bool = Field(default=True, description="Enable auto-reload in development.")


# Single shared instance -- import this rather than constructing a new Settings().
settings = Settings()
