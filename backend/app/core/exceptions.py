class RegBotError(Exception):
    """Base application exception."""


class IngestionError(RegBotError):
    """Raised when ingestion fails."""


class RetrievalError(RegBotError):
    """Raised when retrieval fails."""


class GenerationError(RegBotError):
    """Raised when grounded generation fails."""


class ConfigurationError(RegBotError):
    """Raised when application configuration is invalid."""

