class SapixFilenameError(Exception):
    pass


class PageNumberValidationError(SapixFilenameError):
    pass


class AiExtractionError(SapixFilenameError):
    pass
