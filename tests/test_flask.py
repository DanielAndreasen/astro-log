import datetime
from typing import Tuple

from flask_unittest import ClientTestCase

from astrolog.database import (MODELS, EyePiece, Filter, Location, Object,
                               Observation, Session, Telescope, db)
from astrolog.web.app import app


def get_standard_session() -> Session:
    horsens, _ = Location.get_or_create(name='Horsens', country='Denmark', latitude='55:51:38', longitude='-9:51:1', altitude=0)
    september_13_1989 = datetime.datetime(1989, 9, 13).date()
    session, _ = Session.get_or_create(date=september_13_1989, location=horsens)
    return session


def setup_and_get_equipment() -> Tuple[Telescope, EyePiece, EyePiece, Filter]:
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
        self.assertInResponse(b'Telescopes</a>', response)
        self.assertInResponse(b'Equipment</a>', response)

    def test_get_empty_session(self, client):
        session_id = 1
        response = client.get(f'/session/{session_id}')
        self.assertInResponse('You should be redirected automatically to the target URL: <a href="/">/</a>.'.encode(), response)

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
        # Scenario 3: No telescope
        data = {'object': 'M42', 'magnitude': 4.32,
                'telescope': 'dummy', 'eyepiece': 'Kellner',
                'optical_filter': 'Moon filter', 'note': 'Hold da op!'}
        self.assertLocationHeader(client.post('/observation/new/session/1', data=data), '/observation/new/session/1')
        # Scenario 4: No eyepiece
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
