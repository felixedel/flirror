import abc
from collections import defaultdict, OrderedDict

from flask import current_app, render_template
from flask.views import MethodView

from flirror.exceptions import ModuleDataException


class FlirrorMethodView(MethodView):
    @property
    @abc.abstractmethod
    def endpoint(self):
        pass

    @property
    @abc.abstractmethod
    def rule(self):
        pass

    @property
    @abc.abstractmethod
    def template_name(self):
        pass

    @classmethod
    def register_url(cls, app, **options):
        app.add_url_rule(cls.rule, view_func=cls.as_view(cls.endpoint), **options)

    def get_context(self, **kwargs):
        # Initialize context with meta fields that should be available on all pages
        # E.g. the flirror version or something like this
        context = {}

        # Add additionally provided kwargs
        context = {**context, **kwargs}
        return context


class IndexView(FlirrorMethodView):

    endpoint = "index"
    rule = "/"
    template_name = "index.html"

    def get(self):

        # The dictionary holding all necessary context data for the index template
        # Here we have also place for overall meta data (like flirror version or so)
        ctx_data = {"modules": defaultdict(list)}

        config_modules = current_app.config.get("MODULES", [])

        # Group modules by position and sort positions in asc order
        pos_modules = defaultdict(list)
        for module in config_modules:
            pos_modules[module["display"]["position"]].append(module)
        sort_pos_modules = OrderedDict(sorted(pos_modules.items()))

        for position, module_configs in sort_pos_modules.items():
            for module_config in module_configs:
                module_id = module_config.get("id")
                module_type = module_config.get("type")
                # TODO Error handling for wrong/missing keys

                res = None
                data = None
                error = None
                try:
                    data = current_app.get_module_data(
                        module_id,
                        "raw",
                        f"modules/{module_type}.html",
                        f"module_{module_type}",
                    )
                except ModuleDataException as e:
                    msg = str(e)
                    # If we got a better message from the e.g. JSON API, we use it instead
                    if data is not None and "error" in data:
                        msg = data["msg"]

                    code = 500  # TODO Dump default
                    if res is not None:
                        code = res.status_code
                    error = {"code": code, "msg": msg}

                ctx_data["modules"][position].append(
                    {
                        "type": module_type,
                        "id": module_id,
                        "config": module_config["config"],
                        "display": module_config["display"],
                        "data": data,
                        "error": error,
                    }
                )

        context = self.get_context(**ctx_data)
        return render_template(self.template_name, **context)


class FlirrorApiView(FlirrorMethodView):
    def get(self):
        return current_app.basic_get(self.template_name, self.FLIRROR_OBJECT_KEY)


class CalendarApi(FlirrorApiView):

    endpoint = "api-calendar"
    rule = "/api/calendar"
    template_name = "modules/calendar.html"

    FLIRROR_OBJECT_KEY = "module_calendar"


class NewsfeedApi(FlirrorApiView):

    endpoint = "api-newsfeed"
    rule = "/api/newsfeed"
    template_name = "modules/newsfeed.html"

    FLIRROR_OBJECT_KEY = "module_newsfeed"


class StocksApi(FlirrorApiView):

    endpoint = "api-stocks"
    rule = "/api/stocks"
    template_name = "modules/stocks.html"

    FLIRROR_OBJECT_KEY = "module_stocks"
