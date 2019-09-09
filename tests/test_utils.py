import pytest

from flirror.utils import parse_interval_string


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
    assert (None, None) == parse_interval_string(interval_string)
