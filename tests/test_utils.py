from datetime import datetime

import pytest
from freezegun import freeze_time

from flirror.exceptions import FlirrorConfigError
from flirror.modules import FlirrorModule
from flirror.utils import discover_flirror_modules, parse_interval_string, prettydate


@pytest.mark.parametrize(
    "interval_string, result",
    [
        ("5m", (5, "m")),
        ("10s", (10, "s")),
        ("6483ms", (6483, "ms")),
        ("7h", (7, "h")),
        ("5minutes", (5, "minutes")),
        ("10seconds", (10, "seconds")),
        ("7hours", (7, "hours")),
    ],
)
def test_parse_interval_string(interval_string, result):
    assert result == parse_interval_string(interval_string)


@pytest.mark.parametrize("interval_string", ["m5", "5000", "ms"])
def test_parse_interval_string_failed(interval_string):
    # TODO (felix): These should not match either:
    # - "5 hours"
    with pytest.raises(FlirrorConfigError) as excinfo:
        parse_interval_string(interval_string)

    assert "Could not parse interval string" in str(excinfo.value)


@pytest.mark.parametrize(
    "date, expected",
    [
        ("2018-09-17 10:14:59", "just now"),
        ("2018-09-17 10:12:02", "3 minutes ago"),
        ("2018-09-17 07:12:02", "3 hours ago"),
        ("2018-09-15 07:12:02", "2 days ago"),
        ("2018-06-06 10:25:12", "06. Jun 2018"),
        ("2015-08-14 16:31:07", "14. Aug 2015"),
    ],
)
def test_prettydate(date, expected):
    date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")  # .replace(tzinfo=timezone.utc)
    with freeze_time("2018-09-17 10:15:04"):
        assert expected == prettydate(date)


def test_discover_flirror_modules():
    module_1 = FlirrorModule("module_1", __name__)
    module_2 = FlirrorModule("module_2", __name__)
    module_3 = FlirrorModule("module_3", __name__)

    # As we are mainly relying on the functionality of getattr(), we could mock
    # a plugin module with a simple class providing the necessary attributes.
    class valid_plugin:
        FLIRROR_MODULE = module_1
        FLIRROR_MODULES = [module_2, module_3]

    flirror_modules = discover_flirror_modules({"valid_plugin": valid_plugin})

    # We assume that all modules are valid modules because they are all
    # instances of FlirrorModule.
    assert len(flirror_modules) == 3
    assert flirror_modules == [module_1, module_2, module_3]


def test_discover_flirror_modules_missing_variables():
    class invalid_plugin:
        some_variable = "abc"
        NO_FLIRROR_MODULE = 5

    flirror_modules = discover_flirror_modules({"invalid_plugin": invalid_plugin})

    # As the module does not provide the necessary variables, no modules could
    # be loaded.
    assert flirror_modules == []


def test_discover_flirror_modules_wrong_values():
    module_1 = FlirrorModule("module_1", __name__)
    module_2 = FlirrorModule("module_2", __name__)

    class invalid_plugin:
        FLIRROR_MODULE = [module_1]
        FLIRROR_MODULES = [5, module_2, "abc"]

    flirror_modules = discover_flirror_modules({"invalid_plugin": invalid_plugin})

    # FLIRROR_MODULE cannot be loaded as it does not provide a single element.
    # FLIRROR_MODULES contains some invalid module (not instance of
    # FlirrorModule). Thus, only module_2 is discovered in the end.
    assert flirror_modules == [module_2]
