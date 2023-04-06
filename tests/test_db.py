import datetime
from unittest import TestCase

from peewee import IntegrityError, SqliteDatabase

from astrolog.database import (MODELS, Binocular, Condition, EyePiece, Filter,
                               Location, Object, Observation, Session,
                               Telescope, database_proxy)

db = SqliteDatabase(':memory:')
database_proxy.initialize(db)
db.create_tables(MODELS)


def get_telescope(name: str, aperture: int, focal_length: int) -> Telescope:
    telescope, _ = Telescope.get_or_create(name=name, aperture=aperture, focal_length=focal_length)
    return telescope


def get_binocular(name: str, aperture: int, magnification: int) -> Binocular:
    binocular, _ = Binocular.get_or_create(name=name, aperture=aperture, magnification=magnification)
    return binocular


def get_condition(temperature: int, humidity: int, seeing: float | None = None) -> Condition:
    condition = Condition.create(temperature=temperature, humidity=humidity, seeing=seeing)
    return condition


def get_filter(name: str) -> Filter:
    filter, _ = Filter.get_or_create(name=name)
    return filter


def get_eyepiece(type: str, focal_length: int, width: float) -> EyePiece:
    eyepiece, _ = EyePiece.get_or_create(type=type, focal_length=focal_length, width=width)
    return eyepiece


def get_object(name: str, magnitude: float, favourite: bool = False) -> Object:
    object, _ = Object.get_or_create(name=name, magnitude=magnitude, favourite=favourite)
    return object


def get_location(name: str, country: str, latitude: str, longitude: str, altitude: int) -> Location:
    location, _ = Location.get_or_create(name=name, country=country, latitude=latitude, longitude=longitude, altitude=altitude)
    return location


class TestDB(TestCase):

    def setUp(self) -> None:
        db.create_tables(MODELS)

    def tearDown(self) -> None:
        db.drop_tables(MODELS)

    def test_filter(self) -> None:
        moon_filter = get_filter(name='Moon filter')
        self.assertEqual(moon_filter.name, 'Moon filter')

    def test_eyepiece(self) -> None:
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

    def test_binocular(self) -> None:
        binocular = get_binocular(name='Something', aperture=50, magnification=12)
        self.assertEqual(binocular.name, 'Something')
        self.assertEqual(binocular.aperture, 50)
        self.assertEqual(binocular.magnification, 12)

    def test_telescope(self) -> None:
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

    def test_location(self) -> None:
        horsens = get_location(name='Horsens', country='Denmark', latitude='55:51:38', longitude='-9:51:1', altitude=0)
        self.assertEqual(horsens.name, 'Horsens')
        self.assertEqual(horsens.country, 'Denmark')
        self.assertEqual(horsens.latitude, '55:51:38')
        self.assertEqual(horsens.longitude, '-9:51:1')
        self.assertEqual(horsens.altitude, 0)

    def test_condition(self) -> None:
        condition1 = get_condition(temperature=-2, humidity=65)
        self.assertEqual(condition1.temperature, -2)
        self.assertEqual(condition1.humidity, 65)
        self.assertEqual(condition1.seeing, None)
        condition2 = get_condition(temperature=-2, humidity=65, seeing=1.2)
        self.assertEqual(condition2.seeing, 1.2)
        # Too high humidity
        with self.assertRaises(IntegrityError):
            get_condition(temperature=-2, humidity=101, seeing=1.2)
        # Too low humidity
        with self.assertRaises(IntegrityError):
            get_condition(temperature=-2, humidity=-1, seeing=1.2)

    def test_empty_session(self) -> None:
        horsens = get_location(name='Horsens', country='Denmark', latitude='55:51:38', longitude='-9:51:1', altitude=0)
        september_13_1989 = datetime.datetime(1989, 9, 13).date()
        session, _ = Session.get_or_create(date=september_13_1989, location=horsens)
        self.assertEqual(session.date, september_13_1989)
        self.assertEqual(session.location, horsens)
        self.assertEqual(len(session.observation_set), 0)
        self.assertEqual(session.moon_phase, None)
        self.assertEqual(session.condition, None)
        self.assertEqual(session.number_of_observations, 0)

    def test_session_with_moon_phases(self) -> None:
        horsens = get_location(name='Horsens', country='Denmark', latitude='55:51:38', longitude='-9:51:1', altitude=0)
        september_13_1989 = datetime.datetime(1989, 9, 13).date()
        condition = get_condition(temperature=-2, humidity=65, seeing=1.2)
        session, _ = Session.get_or_create(date=september_13_1989, location=horsens, condition=condition)
        self.assertEqual(session.condition, condition)

    def test_session_with_condition(self) -> None:
        horsens = get_location(name='Horsens', country='Denmark', latitude='55:51:38', longitude='-9:51:1', altitude=0)
        september_13_1989 = datetime.datetime(1989, 9, 13).date()
        session, _ = Session.get_or_create(date=september_13_1989, location=horsens, moon_phase=86)
        self.assertEqual(session.moon_phase, 86)
        # Too high moon_phase
        with self.assertRaises(IntegrityError):
            session, _ = Session.get_or_create(date=september_13_1989, location=horsens, moon_phase=101)
        # Too low moon_phase
        with self.assertRaises(IntegrityError):
            session, _ = Session.get_or_create(date=september_13_1989, location=horsens, moon_phase=-1)

    def test_object(self) -> None:
        arcturus = get_object(name='Arcturus', magnitude=-0.05)
        self.assertEqual(arcturus.name, 'Arcturus')
        self.assertEqual(arcturus.magnitude, -0.05)
        self.assertFalse(arcturus.favourite)
        betelgeuse = get_object(name='Betelgeuse', magnitude=0.45, favourite=True)
        self.assertEqual(betelgeuse.name, 'Betelgeuse')
        self.assertEqual(betelgeuse.magnitude, 0.45)
        self.assertTrue(betelgeuse.favourite)
        arcturus.toggle_favourite()
        arcturus = Object.get(name='Arcturus')
        self.assertTrue(arcturus.favourite)

    def test_observation_with_binocular(self) -> None:
        binocular = get_binocular(name='Something', aperture=50, magnification=12)
        horsens = get_location(name='Horsens', country='Denmark', latitude='55:51:38', longitude='-9:51:1', altitude=0)
        september_13_1989 = datetime.datetime(1989, 9, 13).date()
        session, _ = Session.get_or_create(date=september_13_1989, location=horsens)
        betelgeuse = get_object(name='Betelgeuse', magnitude=0.45)
        observation, _ = Observation.get_or_create(object=betelgeuse, session=session, binocular=binocular)

        self.assertIsNone(observation.note)
        self.assertEqual(observation.session, session)
        self.assertEqual(observation.object, betelgeuse)
        self.assertEqual(observation.binocular, binocular)

    def test_observation_with_telescope(self) -> None:
        plossl = get_eyepiece(type='Plössl', focal_length=6, width=1.25)
        moon_filter = get_filter(name='Moon filter')
        telescope = get_telescope(name='Explorer 150P', aperture=150, focal_length=750)
        telescope.use_eyepiece(plossl)
        magnification = telescope.magnification

        horsens = get_location(name='Horsens', country='Denmark', latitude='55:51:38', longitude='-9:51:1', altitude=0)
        september_13_1989 = datetime.datetime(1989, 9, 13).date()
        session, _ = Session.get_or_create(date=september_13_1989, location=horsens)

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
        self.assertEqual(session.number_of_observations, 2)

    def test_session_with_observations(self) -> None:
        plossl = get_eyepiece(type='Plössl', focal_length=6, width=1.25)
        kellner = get_eyepiece(type='Kellner', focal_length=15, width=1.25)
        telescope = get_telescope(name='Explorer 150P', aperture=150, focal_length=750)

        horsens = get_location(name='Horsens', country='Denmark', latitude='55:51:38', longitude='-9:51:1', altitude=0)
        september_13_1989 = datetime.datetime(1989, 9, 13).date()
        session, _ = Session.get_or_create(date=september_13_1989, location=horsens)

        arcturus = get_object(name='Arcturus', magnitude=-0.05)
        betelgeuse = get_object(name='Betelgeuse', magnitude=0.45)

        Observation.get_or_create(object=betelgeuse, session=session, telescope=telescope, eyepiece=plossl)
        Observation.get_or_create(object=arcturus, session=session, telescope=telescope, eyepiece=kellner)

        self.assertEqual(len(session.observation_set), 2)
        for observation in session.observations:
            self.assertIsNotNone(observation.object)
