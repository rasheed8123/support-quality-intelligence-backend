"""Configuration module for Support Quality Intelligence RAG System"""

from .settings import Settings

# Create global settings instance
settings = Settings()

__all__ = ["settings", "Settings"]
