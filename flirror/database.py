import logging

from pony.orm import Database, db_session, Json, ObjectNotFound, PrimaryKey, Required


LOGGER = logging.getLogger(__name__)

db = Database()


class FlirrorObject(db.Entity):
    key = PrimaryKey(str)
    value = Required(Json)


@db_session
def store_object_by_key(key, value):
    try:
        LOGGER.debug("Updating object with key '%s' in database", key)
        # The most common case is to update an existing entry.
        FlirrorObject[key].value = value
    except ObjectNotFound:
        LOGGER.debug("Object with key '%s' not found, creating a new one", key)
        # If no entry could be found (e.g. calling a crawler for the first time,
        # requesting an initial access token), we have to create one
        FlirrorObject(key=key, value=value)


@db_session
def get_object_by_key(key):
    try:
        LOGGER.debug("Getting object with key '%s' from database", key)
        return FlirrorObject[key].value
    except ObjectNotFound:
        LOGGER.error("Could not get object with key '%s'", key)
        return None


def connect(database_file):
    LOGGER.debug("Using database file '%s'", database_file)
    # Connect to the database and create it if it doesn't exist
    db.bind(provider="sqlite", filename=database_file, create_db=True)

    # Create the tables if they don't exist
    db.generate_mapping(create_tables=True)
