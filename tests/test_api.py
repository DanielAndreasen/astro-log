import datetime
from unittest import TestCase

from peewee import SqliteDatabase

from astrolog import api
from astrolog.database import (MODELS, Binocular, EyePiece, Filter, Location,
                               Object, Observation, Session, Telescope,
                               database_proxy)

db = SqliteDatabase(':memory:')
database_proxy.initialize(db)
db.create_tables(MODELS)


def get_and_create_session_with_n_observations(date: datetime.date, object: Object | None = None, n: int = 1) -> Session:
    location = Location.create(name='Horsens', country='Denmark', latitude='55:51:38', longitude='-9:51:1', altitude=0)
    session = Session.create(date=date, location=location)
    if object is None:
        object = Object.create(name='Betelgeuse', magnitude=0.45)
    telescope = Telescope.create(name='Explorer 150P', aperture=150, focal_length=750)
    plossl = EyePiece.create(type='Plössl', focal_length=6, width=1.25)
    for _ in range(n):
        Observation.create(object=object,
                           session=session,
                           telescope=telescope,
                           eyepiece=plossl)
    return session


class TestDB(TestCase):

    def setUp(self) -> None:
        db.create_tables(MODELS)

    def tearDown(self) -> None:
        db.drop_tables(MODELS)

    def test_get_empty_session(self) -> None:
        date = datetime.datetime(2013, 9, 13).date()
        get_and_create_session_with_n_observations(date, n=1)
        res = api.get_session(date + datetime.timedelta(days=1))
        self.assertIsNone(res['session'])
        self.assertListEqual(res['observations'], [])

    def test_get_session_with_1_observation(self) -> None:
        date = datetime.datetime(2013, 9, 13).date()
        session = get_and_create_session_with_n_observations(date, n=1)
        res = api.get_session(date)
        self.assertEqual(res['session'], session)
        self.assertEqual(len(res['observations']), 1)
        for actual, expected in zip(session.observation_set, res['observations']):
            self.assertEqual(actual, expected)

    def test_get_session_with_5_observation(self) -> None:
        date = datetime.datetime(2013, 9, 13).date()
        session = get_and_create_session_with_n_observations(date, n=5)
        res = api.get_session(date)
        self.assertEqual(res['session'], session)
        self.assertEqual(len(res['observations']), 5)
        for actual, expected in zip(session.observation_set, res['observations']):
            self.assertEqual(actual, expected)

    def test_get_empty_observation(self) -> None:
        betelgeuse = Object.create(name='Betelgeuse', magnitude=0.45)
        rigel = Object.create(name='Rigel', magnitude=-0.45)
        date = datetime.datetime(2013, 9, 13).date()
        get_and_create_session_with_n_observations(date, betelgeuse, n=1)
        res = api.get_observations_of_object(rigel)
        self.assertListEqual(res['observations'], [])

    def test_get_observations_of_object(self) -> None:
        betelgeuse = Object.create(name='Betelgeuse', magnitude=0.45)
        observations = []
        dates = [datetime.datetime(2013, 9, 13).date(), datetime.datetime(2013, 9, 14).date()]
        for date in dates:
            session = get_and_create_session_with_n_observations(date, betelgeuse, n=1)
            observations += list(session.observation_set)
        res = api.get_observations_of_object(betelgeuse)
        self.assertEqual(len(res['observations']), 2)
        for actual, expected in zip(observations, res['observations']):
            self.assertEqual(actual, expected)

    def test_get_empty_sessions(self) -> None:
        date1 = datetime.datetime(2013, 9, 13).date()
        date2 = datetime.datetime(2014, 9, 13).date()
        res = api.get_sessions(date1=date1, date2=date2)
        self.assertListEqual(res['sessions'], [])

    def test_get_sessions(self) -> None:
        date1 = datetime.datetime(2013, 12, 1).date()
        date2 = datetime.datetime(2013, 12, 24).date()
        sessions = []
        for day in range(2, 20):
            date = datetime.datetime(2013, 12, day).date()
            sessions.append(get_and_create_session_with_n_observations(date, n=1))
        res = api.get_sessions(date1=date1, date2=date2)
        self.assertEqual(len(res['sessions']), 20 - 2)
        for actual, expected in zip(sessions, res['sessions']):
            self.assertEqual(actual, expected)

    def test_create_observations(self) -> None:
        date = datetime.datetime(2013, 12, 1).date()
        location = Location.create(name='Horsens', country='Denmark', latitude='55:51:38', longitude='-9:51:1', altitude=0)
        session = Session.create(date=date, location=location)
        betelgeuse = Object.create(name='Betelgeuse', magnitude=0.45, to_be_watched=True)
        telescope = Telescope.create(name='Explorer 150P', aperture=150, focal_length=750)
        eyepiece = EyePiece.create(type='Plössl', focal_length=6, width=1.25)
        optic_filter = Filter.create(name='Moon filter')

        # First observe with telescope
        self.assertTrue(betelgeuse.to_be_watched)
        observation, created = api.create_observation(session, betelgeuse, telescope=telescope, eyepiece=eyepiece, optic_filter=optic_filter)
        self.assertTrue(created)
        self.assertIsInstance(observation, Observation)
        self.assertEqual(observation.session, session)
        self.assertEqual(observation.object, betelgeuse)
        self.assertFalse(observation.object.to_be_watched)
        self.assertEqual(observation.telescope, telescope)
        self.assertEqual(observation.eyepiece, eyepiece)
        self.assertEqual(observation.optic_filter, optic_filter)
        self.assertIsNone(observation.note)
        self.assertIsNone(observation.binocular)
        self.assertFalse(observation.naked_eye)

        # Make the same observation, and see it gives the same result
        observation, created = api.create_observation(session, betelgeuse, telescope=telescope, eyepiece=eyepiece, optic_filter=optic_filter)
        self.assertFalse(created)

        # Make observation with binoculars
        binocular = Binocular.create(name='Something', aperture=50, magnification=12)
        observation, created = api.create_observation(session, betelgeuse, binocular=binocular)
        self.assertTrue(created)
        self.assertIsInstance(observation, Observation)
        self.assertEqual(observation.session, session)
        self.assertEqual(observation.object, betelgeuse)
        self.assertEqual(observation.binocular, binocular)
        self.assertIsNone(observation.telescope)
        self.assertFalse(observation.naked_eye)

        # Make naked eye observation
        observation, created = api.create_observation(session, betelgeuse)
        self.assertTrue(created)
        self.assertIsInstance(observation, Observation)
        self.assertEqual(observation.session, session)
        self.assertEqual(observation.object, betelgeuse)
        self.assertIsNone(observation.binocular)
        self.assertIsNone(observation.telescope)
        self.assertTrue(observation.naked_eye)

    def test_create_observations_nagetives(self) -> None:
        date = datetime.datetime(2013, 12, 1).date()
        location = Location.create(name='Horsens', country='Denmark', latitude='55:51:38', longitude='-9:51:1', altitude=0)
        session = Session.create(date=date, location=location)
        betelgeuse = Object.create(name='Betelgeuse', magnitude=0.45)
        telescope = Telescope.create(name='Explorer 150P', aperture=150, focal_length=750)
        eyepiece = EyePiece.create(type='Plössl', focal_length=6, width=1.25)
        optic_filter = Filter.create(name='Moon filter')
        binocular = Binocular.create(name='Something', aperture=50, magnification=12)

        # Telescope and binocular
        with self.assertRaises(ValueError):
            api.create_observation(session, betelgeuse, telescope=telescope, binocular=binocular)

        # Binocular with eyepiece
        with self.assertRaises(ValueError):
            api.create_observation(session, betelgeuse, binocular=binocular, eyepiece=eyepiece)

        # Binocular with eyepiece
        with self.assertRaises(ValueError):
            api.create_observation(session, betelgeuse, binocular=binocular, optic_filter=optic_filter)

        # Telescope and not eyepiece
        with self.assertRaises(ValueError):
            api.create_observation(session, betelgeuse, telescope=telescope)

    def test_delete_location_without_session(self) -> None:
        location = Location.create(name='Horsens', country='Denmark', latitude='55:51:38', longitude='-9:51:1', altitude=0)
        deleted = api.delete_location(location)
        self.assertTrue(deleted)
        self.assertIsNone(Location.get_or_none(1))

    def test_delete_location_with_session(self) -> None:
        date = datetime.datetime(2013, 12, 1).date()
        location = Location.create(name='Horsens', country='Denmark', latitude='55:51:38', longitude='-9:51:1', altitude=0)
        Session.create(date=date, location=location)
        deleted = api.delete_location(location)
        self.assertFalse(deleted)
        self.assertIsNotNone(Location.get_or_none(1))
        self.assertIsNotNone(Session.get_or_none(1))
