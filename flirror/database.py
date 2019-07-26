from pony.orm import Database, Optional, ormtypes, Required, set_sql_debug, Set

db = Database()


class WeatherBasic(db.Entity):
    date = Required(ormtypes.datetime)
    status = Required(str)
    detailed_status = Required(str)
    icon = Required(str)


class Weather(WeatherBasic):
    city = Required(str)
    temp_cur = Required(float)
    temp_min = Required(float)
    temp_max = Required(float)
    sunrise_time = Required(ormtypes.datetime)
    sunset_time = Required(ormtypes.datetime)
    # foreign-key relation to forecasts
    forecasts = Set("WeatherForecast")


class WeatherForecast(WeatherBasic):
    temp_day = Required(float)
    temp_night = Required(float)
    # foreign-key relation to weather
    weather = Required(Weather)


class Oauth2Credentials(db.Entity):
    date = Required(ormtypes.datetime)
    client_id = Required(str)
    client_secret = Required(str)
    token = Required(str)
    token_uri = Required(str)


class CalendarEvent(db.Entity):
    summary = Required(str)
    start = Required(ormtypes.datetime)
    end = Required(ormtypes.datetime)
    type = Required(str)
    location = Optional(str, nullable=True)


# Connect to the database and create it if it doesn't exist
db.bind(provider="sqlite", filename="database.sqlite", create_db=True)

# Create the tables if they don't exist
db.generate_mapping(create_tables=True)

# Activate pony's debug mode
set_sql_debug(True)
