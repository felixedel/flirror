import importlib
import logging
import pkgutil
import re
from datetime import datetime

import arrow

from flirror.modules import FlirrorModule


LOGGER = logging.getLogger(__name__)


def prettydate(date):
    """
    Return the relative timeframe between the given date and now.
    e.g. 'Just now', 'x days ago', 'x hours ago', ...
    When the difference is greater than 7 days, the timestamp will be returned
    instead.
    """
    # TODO (felix): Make all dates timezone aware.
    # Currently, the dates are not stored with timezone awareness in the database.
    # (How can we do that?). Additionally, not all dates returned by external
    # APIs are timezone aware. Thus, for now just assume that everything is UTC.
    now = datetime.utcnow()
    if isinstance(date, float):
        date = datetime.utcfromtimestamp(date)
    diff = now - date
    # Show the timestamp rather than the relative timeframe when the difference
    # is greater than 7 days
    if diff.days > 7:
        return date.strftime("%d. %b %Y")
    return arrow.get(date).humanize()


def parse_interval_string(interval_string):
    # Split the string into <number><unit>
    pattern = re.compile(r"^(\d+)(\D+)$")
    match = pattern.match(interval_string)

    if not match:
        LOGGER.error("Could not parse interval_string '%s'", interval_string)
        return None, None

    interval = int(match.group(1))
    unit = match.group(2)

    return interval, unit


def format_time(timestamp, format):
    date = datetime.utcfromtimestamp(timestamp)
    return date.strftime(format)


def clean_string(string):
    """
    Taken from Django:
    https://github.com/django/django/blob/e3d0b4d5501c6d0bc39f035e4345e5bdfde12e41/django/utils/text.py#L222

    Return the given string converted to a string that can be used for a clean
    filename. Remove leading and trailing spaces; convert other spaces to
    underscores; and remove anything that is not an alphanumeric, dash,
    underscore, or dot.
    """
    string = str(string).strip().replace(" ", "_").replace("-", "_")
    return re.sub(r"(?u)[^-\w.]", "", string)


def discover_plugins():
    """
    Discover installed flirror plugins following the naming schema 'fliror_*'.

    Find all installed packages starting with 'flirror_' using the pkgutil
    module and returns them.

    For more information, see
    https://packaging.python.org/guides/creating-and-discovering-plugins/
    """
    discovered_plugins = {
        name: importlib.import_module(name)
        for finder, name, ispkg in pkgutil.iter_modules()
        if name.startswith("flirror_")
    }

    LOGGER.debug(
        "Found the following flirror plugins: '%s'",
        "', '".join(discovered_plugins.keys()),
    )

    return discovered_plugins


def discover_flirror_modules(discovered_plugins):
    """
    Look up FlirroModule instances from a list of discovered plugins.

    Search the provided modules for a variable named FLIRROR_MODULE and try to
    load its value as flirror module. If the variable does not point to a valid
    FlirrorModule instance, it will be ignored.

    A plugin could also provide multiple flirror modules via the
    FLIRROR_MODULES variable. In that case, each element will loaded as flirror
    module. If the variable does not point to a valid FlirrorModule instance,
    it will be ignored.

    Returns a list of valid FlirrorModule instances.
    """
    all_discovered_flirror_modules = []
    for package_name, package in discovered_plugins.items():
        discovered_flirror_modules = []
        # The automatic plugin discovery expects modules to be defined in a
        # FLIRROR_MODULES or FLIRROR_MODULES variable.
        # NOTE (felix): We could provide a fallback mechanism that checks
        # every variable in the module to be an instance of FlirrorModule.
        # However, I would not do so as this would only work for top-level
        # variables and not for ones in submodules. Using predefined variable
        # names allows the developers of the plugin to specify their modules
        # even if they are defined in a submodule.

        module = getattr(package, "FLIRROR_MODULE", None)
        if module is not None:
            if isinstance(module, FlirrorModule):
                discovered_flirror_modules.append(module)
            else:
                LOGGER.warning(
                    "Plugin '%s' provides a variable FLIRROR_MODULE, but it's not "
                    "pointing to a valid FlirrorModule instance %s",
                    package_name,
                    module,
                )

        modules = getattr(package, "FLIRROR_MODULES", None)
        if modules is not None:
            for module in modules:
                if isinstance(module, FlirrorModule):
                    discovered_flirror_modules.append(module)
                else:
                    LOGGER.warning(
                        "Plugin '%s' provides a variable FLIRROR_MODULES, but not all "
                        "elements are pointing to a valid FlirrorModule instance: %s",
                        package_name,
                        module,
                    )

        LOGGER.debug(
            "Plugin '%s' provides the following flirror modules '%s'",
            package_name,
            "', '".join(fm.name for fm in discovered_flirror_modules),
        )
        all_discovered_flirror_modules.extend(discovered_flirror_modules)

    return all_discovered_flirror_modules
