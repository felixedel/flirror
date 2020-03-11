from unittest import mock

from click.testing import CliRunner

from flirror.crawler.main import main


def test_main_missing_envvar():
    runner = CliRunner()
    result = runner.invoke(main)
    assert result.exit_code == 1
    assert (
        "The environment variable 'FLIRROR_SETTINGS' is not set and as such "
        "configuration could not be loaded.  Set this variable and make it point "
        "to a configuration file" in str(result.exception)
    )


def test_main_missing_config(monkeypatch):
    monkeypatch.setenv("FLIRROR_SETTINGS", "/invalid/config/path")
    runner = CliRunner()
    result = runner.invoke(main)
    assert result.exit_code == 1
    assert (
        " Unable to load configuration file (No such file or directory): "
        "'/invalid/config/path'" in str(result.exception)
    )


@mock.patch("flirror.crawler.main.SafeScheduler")
def test_crawl_periodic(scheduler_mock, mock_env):
    """Test if the correct jobs are added to the scheduler

    The scheduler itself is mocked, so that nothing runs in the end
    """
    runner = CliRunner()
    # Invoke the crawl command as part of the main group
    result = runner.invoke(main, ["crawl", "--periodic"])

    assert result.exit_code == 0
    assert scheduler_mock.return_value.add_job.call_count == 10

    expected_log_fragments = [
        "Initializing crawler of type 'weather' with id 'weather-frankfurt'",
        "Initializing crawler of type 'weather' with id 'weather-hamburg'",
        "Initializing crawler of type 'calendar' with id 'calendar-my'",
        "Initializing crawler of type 'stocks' with id 'stocks-series'",
        "Initializing crawler of type 'stocks' with id 'stocks-table'",
        "Initializing crawler of type 'newsfeed' with id 'news-tagesschau'",
        "Initializing crawler of type 'newsfeed' with id 'news-nytimes'",
        "Initializing crawler of type 'newsfeed' with id 'news-bbc'",
        "Initializing crawler of type 'calendar' with id 'calendar-authentication'",
        "Initializing crawler of type 'weather' with id 'missing-module'",
    ]

    for fragment in expected_log_fragments:
        assert fragment in result.stdout


def test_crawl_unknown_module(mock_env):
    runner = CliRunner()
    # Invoke the crawl command as part of the main group
    result = runner.invoke(main, ["crawl", "--module", "unknown"])
    assert result.exit_code == 1
    assert (
        "None of the specified modules 'unknown' could be found in the configuration file."
        in result.stdout
    )


def test_crawl_module(mock_env):
    """Test that the crawler for a single module can be run via the cmd line

    The crawler itself is expected to fail as it cannot authenticate against
    the real OWM API with faked test credentials. But showing that the crawler
    is executed is enough for this test.
    """
    runner = CliRunner()
    result = runner.invoke(main, ["crawl", "--module", "weather-frankfurt"])

    assert result.exit_code == 0

    expected_log_fragments = [
        "Initializing crawler of type 'weather' with id 'weather-frankfurt'",
        "Unable to authenticate to OWM API",
        "Execution of job '{'weather-frankfurt'}' failed",
    ]

    for fragment in expected_log_fragments:
        assert fragment in result.stdout
