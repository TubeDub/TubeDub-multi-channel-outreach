class AppError(Exception):
    pass

class NotFound(AppError):
    pass

class PermissionDenied(AppError):
    pass

class ValidationError(AppError):
    pass

class TransitionError(AppError):
    pass

class ProviderError(AppError):
    def __init__(self, message, code=None, retry_after=None):
        super().__init__(message)
        self.code = code
        self.retry_after = retry_after

class RateLimitError(ProviderError):
    pass

class ForbiddenError(ProviderError):
    pass
