import pytest
from jinja2.exceptions import UndefinedError


def test_template_invalid(mock_app):
    # Validates that the other template tests would fail if the data in the database is
    # not sufficient to render a template properly.
    # In that case, the mocked flask app will raise an exception (if a undefined variable
    # is used within a template).
    with pytest.raises(UndefinedError) as excinfo:
        mock_app.get("/api/weather?module_id=weather-hamburg&output=template")

    # City is the first variable that is used within the template
    assert "Variable 'city' is not defined" == str(excinfo.value)


def test_weather_api_template(mock_app):
    # Validating that the template can be rendered successfully should be enough to
    # ensure that the structure of the data is correct. As the API just uses the
    # data from the database and combines it with the config values to fill the template
    # there is no further transformation of that data we could test in here.

    # In case the database contains to less or inconsistent data, the template rendering
    # will fail.

    res = mock_app.get("/api/weather?module_id=weather-frankfurt&output=template")
    assert res.status_code == 200
    assert set(res.json.keys()) == {"_template"}


def test_weather_api_raw(mock_app):
    # For the raw API tests it should be sufficient to check if all expected keys are
    # present in the JSON response.
    res = mock_app.get("/api/weather?module_id=weather-frankfurt&output=raw")
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
