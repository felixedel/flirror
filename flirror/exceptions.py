class CrawlerDataError(Exception):
    """Exception if some data could not be retrieved by a crawler."""

    pass


class GoogleOAuthError(Exception):
    """Exception if the Google OAuth authentication failed."""

    pass


class ModuleDataException(Exception):
    """Exeption if the data for a module could not be retrieved."""

    pass


class FlirrorConfigError(Exception):
    """Exception if any config related value could not be evaluated."""

    pass
