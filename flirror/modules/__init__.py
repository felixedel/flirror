import logging

from flask import Blueprint

LOGGER = logging.getLogger(__name__)


class FlirrorModule(Blueprint):
    _crawler = None

    def crawler(self):
        """Decorate a callable to register it as a crawler for this module"""

        def decorator(f):
            self.register_crawler(f)
            return f

        return decorator

    def register_crawler(self, crawler_callable):
        """Register a callable as crawler for this module"""

        self._crawler = crawler_callable
