import logging

from flask import Blueprint

LOGGER = logging.getLogger(__name__)


class FlirrorModule(Blueprint):
    _crawler = None

    def crawler(self, name):
        """Decorate a callable to register it as a crawler for this module"""

        def decorator(f):
            self.register_crawler(name, f)
            return f

        return decorator

    def register_crawler(self, name, crawler_callable):
        """Register a callable as crawler for this module"""

        LOGGER.debug("Register crawler %s, %s", name, crawler_callable)
        self._crawler = crawler_callable
