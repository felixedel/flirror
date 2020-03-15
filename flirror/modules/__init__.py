import logging

from flask import Blueprint

LOGGER = logging.getLogger(__name__)


class FlirrorModule(Blueprint):
    _crawler = None

    def crawler(self):
        """Decorate a function to register it as a crawler for this module"""

        def decorator(f):
            self.register_crawler(f)
            return f

        return decorator

    def register_crawler(self, crawler_callable):
        """Register a function as crawler for this module"""

        self._crawler = crawler_callable

    def view(self, **options):
        """
        Decorate a function to register it as view for this module.

        This is the same as Flask's route() decorator, but ensures that the
        rule is always set to "/".
        """

        def decorator(f):
            rule = "/"
            endpoint = options.pop("endpoint", f.__name__)
            self.add_url_rule(rule, endpoint, f, **options)
            return f

        return decorator
