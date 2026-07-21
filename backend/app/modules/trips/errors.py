"""Domain and persistence errors for Trip operations."""


class TripError(Exception):
    """Base error for Trip operations."""


class TripNotFoundError(TripError):
    pass


class RevisionNotFoundError(TripError):
    pass


class RevisionConflictError(TripError):
    pass


class PatchValidationError(TripError):
    pass


class ProtectedActivityError(PatchValidationError):
    pass
