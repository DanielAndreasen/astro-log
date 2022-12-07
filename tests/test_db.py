import datetime
from unittest import TestCase

from astrolog.database import (EyePiece, Filter, Object, Observation, Session,
                               Telescope, db)

MODELS = [Session, EyePiece, Filter, Object, Observation, Telescope]


def get_telescope(name, aperture, focal_length):
    telescope, _ = Telescope.get_or_create(name=name, aperture=aperture, focal_length=focal_length)
    return telescope


def get_filter(name):
    filter, _ = Filter.get_or_create(name=name)
    return filter


def get_eyepiece(type, focal_length, width):
    eyepiece, _ = EyePiece.get_or_create(type=type, focal_length=focal_length, width=width)
    return eyepiece


def get_object(name, magnitude):
    object, _ = Object.get_or_create(name=name, magnitude=magnitude)
    return object


class TestDB(TestCase):

    def setUp(self) -> None:
        db.create_tables(MODELS)
        
    def tearDown(self) -> None:
        db.drop_tables(MODELS)

    def test_filter(self):
        moon_filter = get_filter(name='Moon filter')
        self.assertEqual(moon_filter.name, 'Moon filter')

    def test_eyepiece(self):
        plossl = get_eyepiece(type='Plössl', focal_length=6, width=1.25)
        self.assertEqual(plossl.type, 'Plössl')
        self.assertEqual(plossl.focal_length, 6)
        self.assertEqual(plossl.width, 1.25)
        self.assertEqual(plossl.optic_filter, None)
        # Insert filter
        moon_filter = get_filter(name='Moon filter')
        plossl.use_filter(moon_filter)
        self.assertEqual(plossl.optic_filter, moon_filter)
        self.assertEqual(plossl.optic_filter.name, 'Moon filter')
        # Change filter
        red_filter = get_filter(name='Red filter')
        plossl.use_filter(red_filter)
        self.assertEqual(plossl.optic_filter, red_filter)

    def test_telescope(self):
        telescope = get_telescope(name='Explorer 150P', aperture=150, focal_length=750)
        self.assertEqual(telescope.name, 'Explorer 150P')
        self.assertEqual(telescope.aperture, 150)
        self.assertEqual(telescope.focal_length, 750)
        self.assertEqual(telescope.f_ratio, 750 / 150)
        self.assertEqual(telescope.magnification, None)
        # Use one eyepiece
        plossl = get_eyepiece(type='Plössl', focal_length=6, width=1.25)
        magnification1 = telescope.focal_length / plossl.focal_length
        telescope.use_eyepiece(plossl)
        self.assertEqual(telescope.magnification, magnification1)
        # Change eyepiece
        kellner = get_eyepiece(type='Kellner', focal_length=15, width=1.25)
        magnification2 = telescope.focal_length / kellner.focal_length
        telescope = get_telescope(name='Explorer 150P', aperture=150, focal_length=750)
        telescope.use_eyepiece(kellner)
        self.assertEqual(telescope.magnification, magnification2)

    def test_empty_session(self):
        september_13_1989 = datetime.datetime(1989, 9, 13).date()
        session, _ = Session.get_or_create(date=september_13_1989)
        self.assertEqual(session.date, september_13_1989)
        self.assertEqual(len(session.observation_set), 0)

    def test_object(self):
        arcturus = get_object(name='Arcturus', magnitude=-0.05)
        self.assertEqual(arcturus.name, 'Arcturus')
        self.assertEqual(arcturus.magnitude, -0.05)

    def test_observation(self):
        plossl = get_eyepiece(type='Plössl', focal_length=6, width=1.25)
        moon_filter = get_filter(name='Moon filter')
        telescope = get_telescope(name='Explorer 150P', aperture=150, focal_length=750)
        telescope.use_eyepiece(plossl)
        magnification = telescope.magnification

        september_13_1989 = datetime.datetime(1989, 9, 13).date()
        session, _ = Session.get_or_create(date=september_13_1989)

        betelgeuse = get_object(name='Betelgeuse', magnitude=0.45)

        observation = Observation(object=betelgeuse, session=session, telescope=telescope, eyepiece=plossl, optic_filter=moon_filter)
        observation.save()
        self.assertEqual(observation.note, None)
        self.assertEqual(observation.session, session)
        self.assertEqual(observation.object, betelgeuse)
        self.assertEqual(observation.eyepiece, plossl)
        self.assertEqual(observation.optic_filter, moon_filter)
        self.assertEqual(observation.telescope, telescope)
        self.assertEqual(observation.magnification, magnification)

        observation = Observation(object=betelgeuse, session=session, telescope=telescope, eyepiece=plossl, note='Wow, what a view tonight!')
        observation.save()
        self.assertEqual(observation.optic_filter, None)
        self.assertEqual(observation.note, 'Wow, what a view tonight!')

    def test_session_with_observations(self):
        plossl = get_eyepiece(type='Plössl', focal_length=6, width=1.25)
        kellner = get_eyepiece(type='Kellner', focal_length=15, width=1.25)
        telescope = get_telescope(name='Explorer 150P', aperture=150, focal_length=750)

        september_13_1989 = datetime.datetime(1989, 9, 13).date()
        session, _ = Session.get_or_create(date=september_13_1989)

        arcturus = get_object(name='Arcturus', magnitude=-0.05)
        betelgeuse = get_object(name='Betelgeuse', magnitude=0.45)

        Observation.get_or_create(object=betelgeuse, session=session, telescope=telescope, eyepiece=plossl)
        Observation.get_or_create(object=arcturus, session=session, telescope=telescope, eyepiece=kellner)

        self.assertEqual(len(session.observation_set), 2)
        for observation in session.observations:
            self.assertIsNotNone(observation.object)
