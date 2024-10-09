import os

SECRET_KEY = os.urandom(32)
# Grabs the folder where the script runs.
basedir = os.path.abspath(os.path.dirname(__file__))

# Enable debug mode.
DEBUG = True

# Connect to the database
SQL_SERVER = os.environ.get("SQL_SERVER") or "localhost"
SQL_DATABASE = os.environ.get("SQL_DATABASE") or "cd0046"
SQL_USER_NAME = os.environ.get("SQL_USER_NAME") or "postgres"
SQL_PASSWORD = os.environ.get("SQL_PASSWORD") or "123"
SQL_PORT = os.environ.get("SQL_PASSWORD") or "5432"
SQLALCHEMY_DATABASE_URI = (
    "postgresql://"
    + SQL_USER_NAME
    + ":"
    + SQL_PASSWORD
    + "@"
    + SQL_SERVER
    + ":"
    + SQL_PORT
    + "/"
    + SQL_DATABASE
)
