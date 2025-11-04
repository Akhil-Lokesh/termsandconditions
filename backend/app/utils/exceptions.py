"""Custom exceptions for the T&C Analysis System."""


class TCAnalysisException(Exception):
    """Base exception for T&C Analysis System."""

    pass


class DocumentProcessingError(TCAnalysisException):
    """Exception raised when document processing fails."""

    pass


class PDFExtractionError(DocumentProcessingError):
    """Exception raised when PDF text extraction fails."""

    pass


class StructureExtractionError(DocumentProcessingError):
    """Exception raised when structure extraction fails."""

    pass


class InvalidFileTypeError(TCAnalysisException):
    """Exception raised when file type is not supported."""

    pass


class FileSizeExceededError(TCAnalysisException):
    """Exception raised when file size exceeds limit."""

    pass


class OpenAIServiceError(TCAnalysisException):
    """Exception raised when OpenAI API call fails."""

    pass


class EmbeddingError(OpenAIServiceError):
    """Exception raised when embedding generation fails."""

    pass


class LLMCompletionError(OpenAIServiceError):
    """Exception raised when LLM completion generation fails."""

    pass


class PineconeServiceError(TCAnalysisException):
    """Exception raised when Pinecone operation fails."""

    pass


# Alias for backwards compatibility
PineconeError = PineconeServiceError


class CacheServiceError(TCAnalysisException):
    """Exception raised when cache operation fails."""

    pass


class AuthenticationError(TCAnalysisException):
    """Exception raised for authentication failures."""

    pass


class AuthorizationError(TCAnalysisException):
    """Exception raised for authorization failures."""

    pass
