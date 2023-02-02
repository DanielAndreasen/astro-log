import datetime

from flask_unittest import ClientTestCase
from peewee import SqliteDatabase

from astrolog.database import (MODELS, Binocular, EyePiece, Filter, Location,
                               Object, Observation, Session, Telescope,
                               database_proxy)
from astrolog.web.app import app

db = SqliteDatabase(':memory:')
database_proxy.initialize(db)
db.create_tables(MODELS)


def get_standard_session() -> Session:
    horsens, _ = Location.get_or_create(name='Horsens', country='Denmark', latitude='55:51:38', longitude='-9:51:1', altitude=0)
    september_13_1989 = datetime.datetime(1989, 9, 13).date()
    session, _ = Session.get_or_create(date=september_13_1989, location=horsens)
    return session


def setup_and_get_equipment() -> tuple[Telescope, EyePiece, EyePiece, Filter]:
    telescope, _ = Telescope.get_or_create(name='Explorer 150P', aperture=150, focal_length=750)
    plossl, _ = EyePiece.get_or_create(type='Plössl', focal_length=6, width=1.25)
    kellner, _ = EyePiece.get_or_create(type='Kellner', focal_length=15, width=1.25)
    moon_filter, _ = Filter.get_or_create(name='Moon filter')
    return telescope, plossl, kellner, moon_filter


def add_observation(session: Session) -> None:
    telescope, plossl, kellner, moon_filter = setup_and_get_equipment()
    orion_nebula, _ = Object.get_or_create(name='M42', magnitude=5.42)
    moon, _ = Object.get_or_create(name='Moon', magnitude=-14)
    Observation(object=orion_nebula, session=session, telescope=telescope, eyepiece=plossl, note='Saw the trapez stars').save()
    Observation(object=moon, session=session, telescope=telescope, eyepiece=kellner, optic_filter=moon_filter).save()


class TestApp(ClientTestCase):
    app = app

    def setUp(self, client) -> None:
        client
        db.create_tables(MODELS)

    def tearDown(self, client) -> None:
        client
        db.drop_tables(MODELS)

    def test_landing_page(self, client):
        response = client.get('/')
        self.assertStatus(response, 200)
        self.assertInResponse(b'AstroLog</a>', response)
        self.assertInResponse(b'New session</a>', response)
        self.assertInResponse(b'All sessions</a>', response)
        self.assertInResponse(b'Equipment</a>', response)

    def test_get_empty_session(self, client):
        session_id = 1
        response = client.get(f'/session/{session_id}')
        self.assertInResponse('You should be redirected automatically to the target URL: <a href="/">/</a>.'.encode(), response)

    def test_list_all_sessions(self, client):
        self.assertStatus(client.get('/'), 200)
        response = client.get('/session/all')
        self.assertInResponse(b'<th>Date</th>', response)
        self.assertInResponse(b'<th>Location</th>', response)
        self.assertInResponse(b'<th>No. of observations</th>', response)
        self.assertInResponse('<tbody>\n    \n  </tbody'.encode(), response)
        session = get_standard_session()
        response = client.get('/session/all')
        self.assertInResponse(f'<td><a class="btn btn-primary" href="/session/{session.id}">{session.date}</a></td>'.encode(), response)
        self.assertInResponse(f'<td>{session.location.name}</td>'.encode(), response)
        self.assertInResponse(f'<td>{session.number_of_observations}</td>'.encode(), response)

    def test_get_session(self, client):
        response = client.get('/')
        self.assertStatus(response, 200)
        self.assertInResponse(b'All sessions</a>', response)
        session = get_standard_session()
        loc = session.location
        response = client.get('/session/1')
        self.assertStatus(response, 200)
        self.assertInResponse(b'AstroLog', response)
        self.assertInResponse(b'Session', response)
        self.assertInResponse(f'Session - <small>{session.date.strftime("%d/%m/%Y")}</small>'.encode(), response)
        self.assertInResponse(f'Location - <small title="Lat.: {loc.latitude}, Lon.: {loc.longitude}, Alt.: {loc.altitude}m">{session.location.name}</small>'.encode(), response)

        add_observation(session)
        response = client.get('/session/1')
        self.assertInResponse(b'<th>Object</th>', response)
        self.assertInResponse(b'<th>Magnitude</th>', response)
        self.assertInResponse(b'<th>Telescope</th>', response)
        self.assertInResponse(b'<th>Eyepiece</th>', response)
        self.assertInResponse(b'<th>Magnification</th>', response)
        self.assertInResponse(b'<th>Filter</th>', response)
        self.assertInResponse(b'<th>Note</th>', response)
        for observation in session.observations:
            object_name = observation.object.name.encode()
            magnitude = str(observation.object.magnitude).encode()
            telescope_info = f'{observation.telescope.name} (f{observation.telescope.f_ratio})'.encode()
            eyepiece = observation.eyepiece.type.encode()
            magnification = f'{observation.magnification}X'.encode()
            filter_ = observation.optic_filter.name.encode() if observation.optic_filter else ''.encode()
            note = observation.note.encode() if observation.note else ''.encode()
            self.assertInResponse(object_name, response)
            self.assertInResponse(magnitude, response)
            self.assertInResponse(telescope_info, response)
            self.assertInResponse(eyepiece, response)
            self.assertInResponse(magnification, response)
            self.assertInResponse(filter_, response)
            self.assertInResponse(note, response)

    def test_create_session(self, client):
        response = client.get('/')
        self.assertStatus(response, 200)
        self.assertInResponse(b'New session</a>', response)
        response = client.get('/session/new')
        self.assertStatus(response, 200)
        self.assertEqual(len(Session), 0)

        horsens, _ = Location.get_or_create(name='Horsens', country='Denmark', latitude='55:51:38', longitude='-9:51:1', altitude=0)
        response = client.post('/session/new', data={'location': horsens.name, 'date': '1989-09-13'})
        session = Session.get_or_none(1)
        self.assertEqual(len(Session), 1)
        self.assertIsNotNone(session)
        self.assertEqual(session.location.name, horsens.name)
        self.assertEqual(session.date.strftime('%Y-%m-%d'), '1989-09-13')

        # Try to create the same session again
        response = client.post('/session/new', data={'location': horsens.name, 'date': '1989-09-13'})
        self.assertLocationHeader(response, '/observation/new/session/1')

    def test_add_observation_negatives(self, client):
        # No sessions yet
        response = client.get('/observation/new/session/1')
        self.assertLocationHeader(response, '/')

        # Various negative scenarios
        horsens = Location.create(name='Horsens', country='Denmark', latitude='55:51:38', longitude='-9:51:1', altitude=0)
        self.assertLocationHeader(client.post('/session/new', data={'location': horsens.name, 'date': '1989-09-13'}), '/observation/new/session/1')
        setup_and_get_equipment()

        # Scenario 1: No object name
        data = {'magnitude': 4.32,
                'telescope': 'Explorer 150P', 'eyepiece': 'Kellner',
                'optical_filter': 'Moon filter', 'note': 'Hold da op!'}
        self.assertLocationHeader(client.post('/observation/new/session/1', data=data), '/observation/new/session/1')
        # Scenario 2: No object magnitude
        data = {'object': 'M42',
                'telescope': 'Explorer 150P', 'eyepiece': 'Kellner',
                'optical_filter': 'Moon filter', 'note': 'Hold da op!'}
        self.assertLocationHeader(client.post('/observation/new/session/1', data=data), '/observation/new/session/1')
        # Scenario 3: No eyepiece
        data = {'object': 'M42', 'magnitude': 4.32,
                'telescope': 'Explorer 150P', 'eyepiece': 'dummy',
                'optical_filter': 'Moon filter', 'note': 'Hold da op!'}
        self.assertLocationHeader(client.post('/observation/new/session/1', data=data), '/observation/new/session/1')

    def test_add_observation(self, client):
        self.assertInResponse(b'New session</a>', client.get('/'))
        self.assertStatus(client.get('/session/new'), 200)
        horsens = Location.create(name='Horsens', country='Denmark', latitude='55:51:38', longitude='-9:51:1', altitude=0)
        self.assertLocationHeader(client.post('/session/new', data={'location': horsens.name, 'date': '1989-09-13'}), '/observation/new/session/1')
        session = Session.get_or_none(1)
        self.assertIsNotNone(session)

        # Check content on this page
        response = client.get('/observation/new/session/1')
        self.assertInResponse(b'Object*</label>', response)
        self.assertInResponse(b'Magnitude*</label>', response)
        self.assertInResponse(b'Telescope*</label>', response)
        self.assertInResponse(b'Eyepiece*</label>', response)
        self.assertInResponse(b'Filter (optional)</label>', response)
        self.assertInResponse(b'Note (optional)</label>', response)
        self.assertInResponse(b'Add observation</button>', response)

        # Actual make an observation
        self.assertEqual(len(Observation), 0)
        setup_and_get_equipment()
        data = {'object': 'M42', 'magnitude': 4.32,
                'telescope': 'Explorer 150P', 'eyepiece': 'Kellner',
                'optical_filter': 'Moon filter', 'note': 'Hold da op!'}
        response = client.post(f'/observation/new/session/{session.id}', data=data)
        observation = Observation.get_or_none(1)
        loc = session.location
        self.assertIsNotNone(observation)
        self.assertEqual(len(Observation), 1)
        self.assertInResponse(b'Observation created', response)
        self.assertInResponse(f'Session - <small>{session.date.strftime("%d/%m/%Y")}</small>'.encode(), response)
        self.assertInResponse(f'Location - <small title="Lat.: {loc.latitude}, Lon.: {loc.longitude}, Alt.: {loc.altitude}m">{session.location.name}</small>'.encode(), response)

        # Make observation with binocular
        # Create the binocular
        client.post('/equipments/new/binocular', data={'name': 'Vortex Diamondback HD', 'aperture': 50, 'magnification': 12})
        data = {'object': 'M42', 'magnitude': 4.32,
                'binocular': 'Vortex Diamondback HD', 'note': 'Hold da op!'}
        response = client.post(f'/observation/new/session/{session.id}', data=data)
        observation = Observation.get_or_none(2)
        loc = session.location
        self.assertIsNotNone(observation)
        self.assertEqual(len(Observation), 2)
        self.assertInResponse(b'Observation created', response)
        self.assertInResponse(f'Session - <small>{session.date.strftime("%d/%m/%Y")}</small>'.encode(), response)
        self.assertInResponse(f'Location - <small title="Lat.: {loc.latitude}, Lon.: {loc.longitude}, Alt.: {loc.altitude}m">{session.location.name}</small>'.encode(), response)

    def test_list_equipments(self, client):
        telescope, plossl, kellner, moon_filter = setup_and_get_equipment()
        response = client.get('/equipments')

        self.assertStatus(response, 200)
        self.assertInResponse(b'<h2>Telescopes</h2>', response)
        self.assertInResponse(b'<th>Name</th>', response)
        self.assertInResponse(b'<th>Aperture</th>', response)
        self.assertInResponse(b'<th>Focal length</th>', response)
        self.assertInResponse(b'<th>f ratio</th>', response)
        self.assertInResponse(f'<td>{telescope.name}</td>'.encode(), response)
        self.assertInResponse(f'<td>{telescope.aperture}mm</td>'.encode(), response)
        self.assertInResponse(f'<td>{telescope.focal_length}mm</td>'.encode(), response)
        self.assertInResponse(f'<td>{telescope.f_ratio}</td>'.encode(), response)

        self.assertInResponse(b'<h2>Eyepieces</h2>', response)
        self.assertInResponse(b'<th>Type</th>', response)
        self.assertInResponse(b'<th>Focal length</th>', response)
        self.assertInResponse(b'<th>Width</th>', response)
        for eyepiece in (plossl, kellner):
            self.assertInResponse(f'<td>{eyepiece.type}</td>'.encode(), response)
            self.assertInResponse(f'<td>{eyepiece.focal_length}mm</td>'.encode(), response)
            self.assertInResponse(f'<td>{eyepiece.width}"</td>'.encode(), response)

        self.assertInResponse(b'<h2>Filters</h2>', response)
        self.assertInResponse(b'<th>Name</th>', response)
        self.assertInResponse(f'<td>{moon_filter.name}</td>'.encode(), response)

    def test_add_telescope(self, client):
        response = client.get('/equipments')

        self.assertStatus(response, 200)
        self.assertInResponse(b'<button type="submit" class="btn btn-primary">Add telescope</button>', response)
        self.assertInResponse('<tbody>\n        \n      </tbody>'.encode(), response)
        # Negative scenarios - Missing name
        data = {'aperture': 150, 'focal_length': 750}
        self.assertLocationHeader(client.post('/equipments/new/telescope', data=data), '/equipments')
        # Negative scenarios - Missing aperture
        data = {'name': 'Explorer 150P', 'focal_length': 750}
        self.assertLocationHeader(client.post('/equipments/new/telescope', data=data), '/equipments')
        # Negative scenarios - Missing focal length
        data = {'name': 'Explorer 150P', 'aperture': 150}
        self.assertLocationHeader(client.post('/equipments/new/telescope', data=data), '/equipments')
        # Insert data
        data = {'name': 'Explorer 150P', 'aperture': 150, 'focal_length': 750}
        response = client.post('/equipments/new/telescope', data=data)
        telescope = Telescope.get(1)
        response = client.get('/equipments')
        self.assertInResponse(f'<td>{telescope.name}</td>'.encode(), response)
        self.assertInResponse(f'<td>{telescope.aperture}mm</td>'.encode(), response)
        self.assertInResponse(f'<td>{telescope.focal_length}mm</td>'.encode(), response)
        self.assertInResponse(f'<td>{telescope.f_ratio}</td>'.encode(), response)
        # Try create the same telescope again
        self.assertLocationHeader(client.post('/equipments/new/telescope', data=data), '/equipments')

    def test_add_eyepiece(self, client):
        response = client.get('/equipments')

        self.assertStatus(response, 200)
        self.assertInResponse(b'<button type="submit" class="btn btn-primary">Add eyepiece</button>', response)
        self.assertInResponse('<tbody>\n        \n      </tbody>'.encode(), response)
        # Negative scenarios - Missing type
        data = {'focal_length': 6, 'widht': 1.25}
        self.assertLocationHeader(client.post('/equipments/new/eyepiece', data=data), '/equipments')
        # Negative scenarios - Missing focal length
        data = {'type': 'Plössl', 'widht': 1.25}
        self.assertLocationHeader(client.post('/equipments/new/eyepiece', data=data), '/equipments')
        # Negative scenarios - Missing width
        data = {'type': 'Plössl', 'focal_length': 6}
        self.assertLocationHeader(client.post('/equipments/new/eyepiece', data=data), '/equipments')
        # Insert data
        data = {'type': 'Plössl', 'focal_length': 6, 'width': 1.25}
        response = client.post('/equipments/new/eyepiece', data=data)
        eyepiece = EyePiece.get(1)
        response = client.get('/equipments')
        self.assertInResponse(f'<td>{eyepiece.type}</td>'.encode(), response)
        self.assertInResponse(f'<td>{eyepiece.focal_length}mm</td>'.encode(), response)
        self.assertInResponse(f'<td>{eyepiece.width}"</td>'.encode(), response)
        # Try create the same eyepiece again
        self.assertLocationHeader(client.post('/equipments/new/eyepiece', data=data), '/equipments')

    def test_add_filter(self, client):
        response = client.get('/equipments')

        self.assertStatus(response, 200)
        self.assertInResponse(b'<button type="submit" class="btn btn-primary">Add filter</button>', response)
        self.assertInResponse('<tbody>\n        \n      </tbody>'.encode(), response)
        # Negative scenarios - Missing name
        data = {}
        self.assertLocationHeader(client.post('/equipments/new/filter', data=data), '/equipments')
        # Insert data
        data = {'name': 'H alpha'}
        response = client.post('/equipments/new/filter', data=data)
        h_alpha = Filter.get(1)
        response = client.get('/equipments')
        self.assertInResponse(f'<td>{h_alpha.name}</td>'.encode(), response)
        # Try create the same filter again
        self.assertLocationHeader(client.post('/equipments/new/filter', data=data), '/equipments')

    def test_add_binocular(self, client):
        response = client.get('/equipments')

        self.assertStatus(response, 200)
        self.assertInResponse(b'<button type="submit" class="btn btn-primary">Add binocular</button>', response)
        self.assertInResponse('<tbody>\n        \n      </tbody>'.encode(), response)
        # Negative scenarios - Missing name
        data = {}
        self.assertLocationHeader(client.post('/equipments/new/binocular', data=data), '/equipments')
        # Insert data
        data = {'name': 'Vortex Diamondback HD', 'aperture': 50, 'magnification': 12}
        response = client.post('/equipments/new/binocular', data=data)
        vortex = Binocular.get(1)
        response = client.get('/equipments')
        self.assertInResponse(f'<td>{vortex.name}</td>'.encode(), response)
        self.assertInResponse(f'<td>{vortex.aperture}mm</td>'.encode(), response)
        self.assertInResponse(f'<td>{vortex.magnification}X</td>'.encode(), response)
        # Try create the same filter again
        self.assertLocationHeader(client.post('/equipments/new/binocular', data=data), '/equipments')

    def test_add_location(self, client):
        response = client.get('/locations')

        # No locations added yet
        self.assertStatus(response, 200)
        self.assertInResponse(b'<h2>Locations</h2>', response)
        self.assertInResponse(b'<h2>Locations</h2>', response)
        self.assertInResponse(b'<th>Name</th>', response)
        self.assertInResponse(b'<th>Country</th>', response)
        self.assertInResponse(b'<th>Latitude</th>', response)
        self.assertInResponse(b'<th>Longitude</th>', response)
        self.assertInResponse(b'<th>Altitude</th>', response)
        self.assertInResponse(b'<tbody>\n    \n  </tbody>', response)
        self.assertInResponse(b'<button type="submit" class="btn btn-primary">Add location</button>', response)

        # Add a location
        data = {'name': 'Horsens', 'country': 'Denmark', 'latitude': '55:51:38', 'longitude': '-9:51:1', 'altitude': 0}
        response = client.post('/locations/new', data=data)
        self.assertLocationHeader(response, '/locations')
        # Create same location again (nothing happens)
        self.assertLocationHeader(client.post('/locations/new', data=data), '/locations')

        # Check content of the added location
        response = client.get('/locations')
        location = Location.get(1)
        self.assertStatus(response, 200)
        self.assertInResponse(b'<h2>Locations</h2>', response)
        self.assertInResponse(f'<td>{location.name}</td>'.encode(), response)
        self.assertInResponse(f'<td>{location.country}</td>'.encode(), response)
        self.assertInResponse(f'<td>{location.latitude}</td>'.encode(), response)
        self.assertInResponse(f'<td>{location.longitude}</td>'.encode(), response)
        self.assertInResponse(f'<td>{location.altitude}</td>'.encode(), response)
        location = Location.get_or_none(2)
        self.assertIsNone(location)

    def test_add_location_negatives(self, client):
        # Add a location - no name
        data = {'country': 'Denmark', 'latitude': '55:51:38', 'longitude': '-9:51:1', 'altitude': 0}
        response = client.post('/locations/new', data=data)
        self.assertLocationHeader(response, '/locations')
        # Add a location - no country
        data = {'name': 'Horsens', 'latitude': '55:51:38', 'longitude': '-9:51:1', 'altitude': 0}
        response = client.post('/locations/new', data=data)
        self.assertLocationHeader(response, '/locations')
        # Add a location - no latitude
        data = {'name': 'Horsens', 'country': 'Denmark', 'longitude': '-9:51:1', 'altitude': 0}
        response = client.post('/locations/new', data=data)
        self.assertLocationHeader(response, '/locations')
        # Add a location - no longitude
        data = {'name': 'Horsens', 'country': 'Denmark', 'latitude': '55:51:38', 'altitude': 0}
        response = client.post('/locations/new', data=data)
        self.assertLocationHeader(response, '/locations')
        # Add a location - no altitude
        data = {'name': 'Horsens', 'country': 'Denmark', 'latitude': '55:51:38', 'longitude': '-9:51:1'}
        response = client.post('/locations/new', data=data)
        self.assertLocationHeader(response, '/locations')
