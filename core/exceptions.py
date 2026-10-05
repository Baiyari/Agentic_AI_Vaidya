class VaidyaError(Exception):
    """Base exception for Vaidya domain errors."""
    pass

class InvalidSymptomError(VaidyaError):
    """Raised when an unknown or invalid symptom is provided."""
    pass

class TriageValidationError(VaidyaError):
    """Raised when inputs for triage fail domain validation."""
    pass
