import abc
from collections import defaultdict, OrderedDict
from typing import Any, Dict

from flask import current_app, render_template
from flask.views import MethodView


class FlirrorMethodView(MethodView):
    @property
    @abc.abstractmethod
    def endpoint(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def rule(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def template_name(self) -> str:
        pass

    @classmethod
    # TODO (felix): mypy -> When type annotating this function, mypy complains
    # about:
    # Argument 1 to "add_url_rule" of "Flask" has incompatible type
    # "Callable[[FlirrorMethodView], str]"; expected "str"
    def register_url(cls, app, **options):
        app.add_url_rule(cls.rule, view_func=cls.as_view(cls.endpoint), **options)

    def get_context(self, **kwargs: Any) -> Dict[str, Any]:
        # Initialize context with meta fields that should be available on all pages
        # E.g. the flirror version or something like this
        context: Dict[str, Any] = {}

        # Add additionally provided kwargs
        context = {**context, **kwargs}
        return context


class IndexView(FlirrorMethodView):

    endpoint = "index"
    rule = "/"
    template_name = "index.html"

    def get(self) -> str:
        # The dictionary holding all necessary context data for the index
        # template. Here we have also place for overall meta data (like flirror
        # version or so).
        ctx_data: Dict[str, Any] = {
            "tiles": defaultdict(list),
            "unpositioned_tiles": [],
        }

        config_modules = current_app.config.get("MODULES", [])

        # Group modules by position and sort positions in asc order
        pos_modules = defaultdict(list)
        # Modules without position information will always be placed after the
        # positioned modules.
        unpos_modules = []
        for module in config_modules:
            pos = module.get("display", {}).get("position")
            if pos is not None:
                pos_modules[pos].append(module)
            else:
                unpos_modules.append(module)
        sort_pos_modules = OrderedDict(sorted(pos_modules.items()))

        for position, module_configs in sort_pos_modules.items():
            for module_config in module_configs:
                ctx_data["tiles"][position].append(self._get_module_info(module_config))

        for module_config in unpos_modules:
            ctx_data["unpositioned_tiles"].append(self._get_module_info(module_config))

        context = self.get_context(**ctx_data)
        return render_template(self.template_name, **context)

    @staticmethod
    def _get_module_info(module_config):
        module_id = module_config.get("id")
        # TODO (felix): Remove this fallback in a later future version
        module_name = module_config.get("module") or module_config.get("type")
        # TODO Error handling for wrong/missing keys

        # NOTE (felix): The index view will only ensure that the
        # modules are positioned properly. The content of each tile
        # will be loaded asynchronously via ajax.
        return {
            "id": module_id,
            "name": module_name,
            "config": module_config.get("config"),
            "display": module_config.get("display"),
        }
