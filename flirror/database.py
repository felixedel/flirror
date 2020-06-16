import logging
from typing import Dict, Optional

from pony.orm import Database, db_session, Json, ObjectNotFound, PrimaryKey, Required


LOGGER = logging.getLogger(__name__)


def create_database_and_entities(**db_params):
    db: Database = Database()

    # How to use separated databases for prod and testing:
    # https://github.com/ponyorm/pony/issues/32
    class FlirrorObject(db.Entity):
        key = PrimaryKey(str)
        value = Required(Json)

    LOGGER.debug(
        "Creating new database connection with the following parameters: %s", db_params
    )
    # Connect to the database and create it if it doesn't exist
    db.bind(**db_params)

    # Create the tables if they don't exist
    db.generate_mapping(create_tables=True)

    return db


@db_session
def store_object_by_key(db: Database, key: str, value: Dict) -> None:
    # TODO Store timezone aware dates in the database. Most probably, we must
    # provide a custom JSON serializer to pony orm (how can we do that?) to
    # store datetime objects rather than plain timestamps in the database.
    try:
        LOGGER.debug("Updating object with key '%s' in database", key)
        # The most common case is to update an existing entry.
        db.FlirrorObject[key].value = value
    except ObjectNotFound:
        LOGGER.debug("Object with key '%s' not found, creating a new one", key)
        # If no entry could be found (e.g. calling a crawler for the first time,
        # requesting an initial access token), we have to create one
        db.FlirrorObject(key=key, value=value)


@db_session
def get_object_by_key(db: Database, key: str) -> Optional[Dict]:
    try:
        LOGGER.debug("Getting object with key '%s' from database", key)
        return db.FlirrorObject[key].value
    except ObjectNotFound:
        LOGGER.error("Could not get object with key '%s'", key)
        return None
