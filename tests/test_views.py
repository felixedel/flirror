import pytest
from jinja2.exceptions import UndefinedError


def test_template_invalid(mock_app):
    # Validates that the other template tests would fail if the data in the database is
    # not sufficient to render a template properly.
    # In that case, the mocked flask app will raise an exception (if a undefined variable
    # is used within a template).
    with pytest.raises(UndefinedError) as excinfo:
        mock_app.get("/weather/?module_id=weather-hamburg&output=template")

    # City is the first variable that is used within the template
    assert "Variable 'city' is not defined" == str(excinfo.value)


def test_weather_api_template(mock_app):
    # Validating that the template can be rendered successfully should be enough to
    # ensure that the structure of the data is correct. As the API just uses the
    # data from the database and combines it with the config values to fill the template
    # there is no further transformation of that data we could test in here.

    # In case the database contains to less or inconsistent data, the template rendering
    # will fail.

    res = mock_app.get("/weather/?module_id=weather-frankfurt&output=template")
    assert res.status_code == 200
    assert set(res.json.keys()) == {"_template"}


def test_weather_api_raw(mock_app):
    # For the raw API tests it should be sufficient to check if all expected keys are
    # present in the JSON response.
    res = mock_app.get("/weather/?module_id=weather-frankfurt&output=raw")
    assert res.status_code == 200
    assert set(res.json.keys()) == {
        "_timestamp",
        "city",
        "date",
        "detailed_status",
        "icon",
        "status",
        "sunrise_time",
        "sunset_time",
        "temp_cur",
        "temp_max",
        "temp_min",
        "forecasts",
    }

    assert len(res.json["forecasts"]) == 6

    assert set(res.json["forecasts"][0].keys()) == {
        "date",
        "detailed_status",
        "icon",
        "status",
        "temp_day",
        "temp_night",
    }


def test_calendar_api_template(mock_app):
    res = mock_app.get("/calendar/?module_id=calendar-my&output=template")
    assert res.status_code == 200
    assert set(res.json.keys()) == {"_template"}


def test_calendar_api_authentication_template(mock_app):
    res = mock_app.get("/calendar/?module_id=calendar-authentication&output=template")
    assert res.status_code == 200
    assert set(res.json.keys()) == {"_template"}


def test_calendar_api_raw(mock_app):
    res = mock_app.get("/calendar/?module_id=calendar-my&output=raw")
    assert res.status_code == 200
    assert set(res.json.keys()) == {"_timestamp", "events"}

    assert len(res.json["events"]) == 5

    assert set(res.json["events"][0].keys()) == {
        "end",
        "location",
        "start",
        "summary",
        "type",
    }


def test_newsfeed_api_template(mock_app):
    res = mock_app.get("/api/newsfeed?module_id=news-tagesschau&output=template")
    assert res.status_code == 200
    assert set(res.json.keys()) == {"_template"}


def test_newsfeed_api_raw(mock_app):
    res = mock_app.get("/api/newsfeed?module_id=news-tagesschau&output=raw")
    assert res.status_code == 200
    assert set(res.json.keys()) == {"_timestamp", "news"}

    assert len(res.json["news"]) == 3

    assert set(res.json["news"][0].keys()) == {"link", "published", "summary", "title"}


def test_stocks_api_template_series(mock_app):
    res = mock_app.get("/api/stocks?module_id=stocks-series&output=template")
    assert res.status_code == 200
    assert set(res.json.keys()) == {"_template"}


def test_stocks_api_raw_series(mock_app):
    res = mock_app.get("/api/stocks?module_id=stocks-series&output=raw")
    assert res.status_code == 200
    assert set(res.json.keys()) == {"_timestamp", "stocks"}

    assert len(res.json["stocks"]) == 1

    assert set(res.json["stocks"][0].keys()) == {"alias", "data"}

    assert set(res.json["stocks"][0]["data"].keys()) == {"times", "values"}
    assert len(res.json["stocks"][0]["data"]["times"]) == 5
    assert len(res.json["stocks"][0]["data"]["values"]) == 5


def test_stocks_api_template_table(mock_app):
    res = mock_app.get("/api/stocks?module_id=stocks-table&output=template")
    assert res.status_code == 200
    assert set(res.json.keys()) == {"_template"}


def test_stocks_api_raw_table(mock_app):
    res = mock_app.get("/api/stocks?module_id=stocks-table&output=raw")
    assert res.status_code == 200
    assert set(res.json.keys()) == {"_timestamp", "stocks"}

    assert len(res.json["stocks"]) == 3

    assert set(res.json["stocks"][0].keys()) == {"alias", "data", "symbol"}


def test_invalid_api(mock_app):
    res = mock_app.get("/api/invalid")
    assert res.status_code == 404
    assert not res.json


def test_api_missing_parameter(mock_app):
    res = mock_app.get(f"/weather/?module_id=some-module")
    assert res.status_code == 400
    assert res.json == {
        "error": 400,
        "msg": "Missing 'output' parameter. Must be one of: ['template', 'raw'].",
    }


def test_api_invalid_module_id(mock_app):
    res = mock_app.get(f"/weather/?module_id=invalid-module&output=raw")
    assert res.status_code == 400
    assert res.json == {
        "error": 400,
        "msg": "Could not find any module config for ID 'invalid-module'. "
        "Are you sure this one is specified in the config file?",
    }
