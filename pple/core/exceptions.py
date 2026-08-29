class PPLEError(Exception):
    """Base class for all pple package errors."""


class ModuleValidationError(PPLEError):
    """Raised by EngineeringModule.validate() when input data is unusable."""


class ModuleNotRegisteredError(PPLEError):
    """Raised by ModuleRegistry.get() when no module is registered under that id."""
