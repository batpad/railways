## Django Project to import, view and manage Indian Railways data [WIP]

### Setup

 - Assumes you have Postgres with PostGIS installed on your machine.
 - Create a virtualenv
 - `pip install -r requirements.txt`
 - `createdb railways`
 - `psql railways`
 - `CREATE EXTENSION postgis`
 - `\q`
 - `python manage.py migrate`

### Import Data

This assumes you have all the data required locally.

`python manage.py shell` to open the django shell and then:
`from india.models import *` to import all models. Then:

Import Stations: `Station.import_from_csv('/path/to/file.csv')`

Import Trains: `Train.import_from_csv('/path/to/file.csv')`

Import Schedules: `Schedule.import_from_json('/path/to/file.json')`

Associate Stations with lat-lngs: `Station.import_locations('/path/to/json')` (you may want to change this based on your source for lat-lngs - look at the `import_locations` classmethod of the `Station` model)

### Have fun!

Look at the existing model and class methods to see what data you can export - try running them on your shell! Add more methods to extract interesting data and make Pull Reqeusts!

### Next Steps

Coming Soon: An admin interface to manage and edit data + some front-end to browse and visualize data.

Happy data-ing!