class CrawlerConfigError(Exception):
    """Exception if a crawler could not be initialized correctly."""

    pass


class CrawlerDataError(Exception):
    """Exception if some data could not be retrieved by a crawler."""

    pass


class GoogleOAuthError(Exception):
    """Exception if the Google OAuth authencitaion failed."""

    pass


class ModuleDataException(Exception):
    """Exeption if the data for a module could not be retrieved."""

    pass
