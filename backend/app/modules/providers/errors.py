"""Errors raised by travel data providers."""


class ProviderError(Exception):
    """Base provider error safe for fallback handling."""


class ProviderConfigurationError(ProviderError):
    pass


class ProviderResponseError(ProviderError):
    pass


class ProviderUnavailableError(ProviderError):
    pass
