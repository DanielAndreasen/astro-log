[![CI](https://github.com/DanielAndreasen/astro-log/actions/workflows/main.yml/badge.svg?branch=master)](https://github.com/DanielAndreasen/astro-log/actions/workflows/main.yml)

# Astro log
Website to implement logs for (amateur) astronomical observations.

# Screenshots
## Add and view your equipment
![Equipments](screenshots/equipments.png)
## List objects observed, favourites, and to-be-watched
![Objects](screenshots/objects.png)
## Add a new observation - choose a type
![Observation types](screenshots/observation_types.png)
## Add a new observation
![New observation](screenshots/new_observation.png)
## List all observation sessions
![All sessions](screenshots/all_sessions.png)
## Show details for a given session
![Session details](screenshots/session_details.png)

# Getting started
## Without docker

Create a virtualenv with `virtualenv -p pythton3 venv` and activate it
with `source venv/bin/activate`.

Install dependencies with e.g. `pip install -e .` which also allows
development.

Run the tests (optional, but good sanity check) with `pytest --cov=astrolog --cov-report term-missing`.

Run the web application with `python src/astrolog/web/app.py` and follow
the instructions from the prompt.

# With docker
Just do `docker-compose up -d` and go to [http:localhost:5065](http:localhost:5065)
