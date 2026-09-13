"""Domain errors raised while processing bank statements."""


class StatementError(Exception):
    """Base class for expected statement-processing failures."""


class InvalidPdfError(StatementError):
    """Raised when the input is not a readable PDF."""


class EncryptedPdfError(StatementError):
    """Raised when the input PDF is password protected."""


class TextExtractionError(StatementError):
    """Raised when a PDF does not expose extractable text."""


class UnsupportedStatementError(StatementError):
    """Raised when a document does not match a supported statement format."""


class UnreliableExtractionError(StatementError):
    """Raised when required statement data cannot be extracted reliably."""
