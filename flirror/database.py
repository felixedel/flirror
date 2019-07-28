from pony.orm import (
    Database,
    db_session,
    Json,
    ObjectNotFound,
    Optional,
    ormtypes,
    PrimaryKey,
    Required,
    # set_sql_debug,
    Set,
)

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


class CalendarEvent(db.Entity):
    summary = Required(str)
    start = Required(ormtypes.datetime)
    end = Required(ormtypes.datetime)
    type = Required(str)
    location = Optional(str, nullable=True)


class FlirrorObject(db.Entity):
    key = PrimaryKey(str)
    value = Required(Json)


# Connect to the database and create it if it doesn't exist
db.bind(provider="sqlite", filename="database.sqlite", create_db=True)

# Create the tables if they don't exist
db.generate_mapping(create_tables=True)

# Activate pony's debug mode
# set_sql_debug(True)


@db_session
def store_object_by_key(key, value):
    try:
        # The most common case is to update an existing entry.
        FlirrorObject[key].value = value
    except ObjectNotFound:
        # If no entry could be found (e.g. calling a crawler for the first time,
        # requesting an initial access token), we have to create one
        FlirrorObject(key=key, value=value)


@db_session
def get_object_by_key(key):
    try:
        return FlirrorObject[key].value
    except ObjectNotFound:
        # TODO Log exception, which logger?
        print("Could not get object with key '{}'".format(key))
        return None
