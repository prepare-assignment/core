class PrepareError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ValidationError(PrepareError):

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class DependencyError(PrepareError):

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class PrepareTaskError(PrepareError):

    def __init__(self, message: str, cause: Exception):
        super().__init__(message)
        self.message = message
        self.cause = cause
