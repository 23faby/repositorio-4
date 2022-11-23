#!/bin/sh

export DB_URI=postgresql://myuser:mypassword@localhost:35432/simplelogin
echo 'drop schema public cascade; create schema public;' | psql  $DB_URI

poetry run alembic upgrade head
poetry run flask dummy-data
