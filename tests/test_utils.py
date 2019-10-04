from datetime import datetime

import pytest
from freezegun import freeze_time

from flirror.utils import parse_interval_string, prettydate


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
