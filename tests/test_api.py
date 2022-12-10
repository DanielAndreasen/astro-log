import datetime
from unittest import TestCase

from astrolog import api
from astrolog.database import (Condition, EyePiece, Filter, Location, Object,
                               Observation, Session, Telescope, db)

MODELS = [Condition, Session, EyePiece, Filter, Location, Object, Observation, Telescope]


def get_and_create_session_with_n_observations(date, object=None, n=1):
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

    def test_get_empty_session(self):
        date = datetime.datetime(2013, 9, 13).date()
        get_and_create_session_with_n_observations(date, n=1)
        res = api.get_session(date + datetime.timedelta(days=1))
        self.assertIsNone(res['session'])
        self.assertListEqual(res['observations'], [])

    def test_get_session_with_1_observation(self):
        date = datetime.datetime(2013, 9, 13).date()
        session = get_and_create_session_with_n_observations(date, n=1)
        res = api.get_session(date)
        self.assertEqual(res['session'], session)
        self.assertEqual(len(res['observations']), 1)
        for actual, expected in zip(session.observation_set, res['observations']):
            self.assertEqual(actual, expected)

    def test_get_session_with_5_observation(self):
        date = datetime.datetime(2013, 9, 13).date()
        session = get_and_create_session_with_n_observations(date, n=5)
        res = api.get_session(date)
        self.assertEqual(res['session'], session)
        self.assertEqual(len(res['observations']), 5)
        for actual, expected in zip(session.observation_set, res['observations']):
            self.assertEqual(actual, expected)

    def test_get_empty_observation(self):
        betelgeuse = Object.create(name='Betelgeuse', magnitude=0.45)
        rigel = Object.create(name='Rigel', magnitude=-0.45)
        date = datetime.datetime(2013, 9, 13).date()
        get_and_create_session_with_n_observations(date, betelgeuse, n=1)
        res = api.get_observations_of_object(rigel)
        self.assertListEqual(res['observations'], [])

    def test_get_observations_of_object(self):
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

    def test_get_empty_sessions(self):
        date1 = datetime.datetime(2013, 9, 13).date()
        date2 = datetime.datetime(2014, 9, 13).date()
        res = api.get_sessions(date1=date1, date2=date2)
        self.assertListEqual(res['sessions'], [])

    def test_get_sessions(self):
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
