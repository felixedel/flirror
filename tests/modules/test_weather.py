from unittest import mock

import pytest
import requests_mock
from freezegun import freeze_time

from flirror.exceptions import CrawlerConfigError, CrawlerDataError
from flirror.modules.weather import crawl


def test_crawl(load_fixture_file):
    mocked_app = mock.Mock()
    with requests_mock.mock() as m, freeze_time("2020-08-22"):
        m.get(
            "https://api.openweathermap.org/data/2.5/onecall",
            json=load_fixture_file("modules/weather/fake_api_response.json"),
        )
        crawl(
            module_id="test_module",
            app=mocked_app,
            api_key="my-secret-api-key",
            # Those values don't matter for the test as we only have one fake
            # response.
            city="Frankfurt am Main, DE",
            lat=50.11,
            lon=8.68,
        )

    data_stored = mocked_app.store_module_data.call_args_list[0][0]
    # database entry key
    key = data_stored[0]
    # database entry value
    value = data_stored[1]

    assert key == "test_module"
    expected_value = {
        "_timestamp": 1598054400.0,
        "city": "Frankfurt am Main, DE",
        "date": 1598047004,
        "detailed_status": "overcast clouds",
        "icon": "04n",
        "lat": 50.11,
        "lon": 8.68,
        "status": "Clouds",
        "sunrise_time": 1597983856,
        "sunset_time": 1598034768,
        "temp_cur": 27.2,
        "temp_day": None,
        "temp_max": 27.2,
        "temp_min": 25.08,
        "temp_night": None,
    }
    # Ensure that all expected values are part of the stored value
    # We could also use the following shorthand, but in case of an error the
    # message is not helpful at all:
    # assert expected_value.items() <= value.items()
    for k, v in expected_value.items():
        assert v == value[k]

    # Ensure that there are 6 forecasts entries and verify the structure of the
    # first entry
    assert len(value["forecasts"]) == 6
    assert value["forecasts"][0] == {
        "date": 1598094000,
        "detailed_status": "light rain",
        "icon": "10d",
        "status": "Rain",
        "sunrise_time": 1598070347,
        "sunset_time": 1598121048,
        "temp_cur": None,
        "temp_day": 25.38,
        "temp_night": 20.56,
    }


def test_crawl_unknown_city(load_fixture_file):
    # The city lookup is local (the city list is packaged into pyowm), so we
    # don't need to mock the API here.
    with pytest.raises(CrawlerDataError) as excinfo:
        crawl(
            module_id="test_module",
            app=None,
            api_key="my-secret-api-key",
            # Those values don't matter for the test as we only have one fake
            # response.
            city="Unknown city, DE",
        )
    assert (
        "Could not find 'Unknown city, DE' in city registry. Please specify "
        "the corresponding lat/lon values directly in the module's config."
        == str(excinfo.value)
    )


def test_crawl_missing_parameters():
    with pytest.raises(CrawlerConfigError) as excinfo:
        crawl(module_id="test_module", app=None, api_key="my-secret-api-key")

    assert "Either lat and lon or the city parameter must be provided" == str(
        excinfo.value
    )
