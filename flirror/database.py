from pony.orm import Database, db_session, Json, ObjectNotFound, PrimaryKey, Required

db = Database()


class FlirrorObject(db.Entity):
    key = PrimaryKey(str)
    value = Required(Json)


# Connect to the database and create it if it doesn't exist
db.bind(provider="sqlite", filename="database.sqlite", create_db=True)

# Create the tables if they don't exist
db.generate_mapping(create_tables=True)


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
