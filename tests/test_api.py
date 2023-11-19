import datetime
import random
from unittest import TestCase

from peewee import SqliteDatabase

from astrolog import api
from astrolog.database import (
    MODELS,
    Barlow,
    Binocular,
    Camera,
    EyePiece,
    Filter,
    FrontFilter,
    Location,
    Object,
    Observation,
    Session,
    Telescope,
    database_proxy,
)
from astrolog.report import Report

db = SqliteDatabase(":memory:")
database_proxy.initialize(db)
db.create_tables(MODELS)


def get_and_create_session_with_n_observations(
    date: datetime.date, object: Object | None = None, n: int = 1
) -> Session:
    location = Location.create(
        name="Horsens",
        country="Denmark",
        latitude="55:51:38",
        longitude="-9:51:1",
        altitude=0,
    )
    session = Session.create(date=date, location=location)
    if object is None:
        object = Object.create(name="Betelgeuse")
    telescope = Telescope.create(name="Explorer 150P", aperture=150, focal_length=750)
    plossl = EyePiece.create(type="Plössl", focal_length=6, width=1.25)
    for _ in range(n):
        Observation.create(
            object=object, session=session, telescope=telescope, eyepiece=plossl
        )
    return session


class TestAPI(TestCase):
    def setUp(self) -> None:
        db.create_tables(MODELS)

    def tearDown(self) -> None:
        db.drop_tables(MODELS)

    def test_create_observations(self) -> None:
        date = datetime.datetime(2013, 12, 1).date()
        location = Location.create(
            name="Horsens",
            country="Denmark",
            latitude="55:51:38",
            longitude="-9:51:1",
            altitude=0,
        )
        session = Session.create(date=date, location=location)
        betelgeuse = Object.create(name="Betelgeuse", to_be_watched=True)
        telescope = Telescope.create(
            name="Explorer 150P", aperture=150, focal_length=750
        )
        eyepiece = EyePiece.create(type="Plössl", focal_length=6, width=1.25)
        barlow = Barlow.create(name="Barlow", multiplier=2)
        camera = Camera.create(
            manufacture="Bresser", model="HD Moon, planet, and guiding", megapixel=1.2
        )
        optic_filter = Filter.create(name="Moon filter")
        solar_filter = FrontFilter.create(name="Moon filter")

        # First observe with telescope
        self.assertTrue(betelgeuse.to_be_watched)
        observation, created = api.create_observation(
            session,
            betelgeuse,
            telescope=telescope,
            eyepiece=eyepiece,
            barlow=barlow,
            optic_filter=optic_filter,
            front_filter=solar_filter,
        )
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
        observation, created = api.create_observation(
            session,
            betelgeuse,
            telescope=telescope,
            eyepiece=eyepiece,
            barlow=barlow,
            optic_filter=optic_filter,
            front_filter=solar_filter,
        )
        self.assertFalse(created)

        # Make observation with binoculars
        binocular = Binocular.create(name="Something", aperture=50, magnification=12)
        observation, created = api.create_observation(
            session, betelgeuse, binocular=binocular
        )
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

        # Make an observation with telescope and dedicated camera
        observation, created = api.create_observation(
            session,
            betelgeuse,
            telescope=telescope,
            camera=camera,
            optic_filter=optic_filter,
        )
        self.assertTrue(created)
        self.assertEqual(observation.telescope, telescope)
        self.assertEqual(observation.camera, camera)
        self.assertEqual(observation.optic_filter, optic_filter)
        self.assertIsNone(observation.eyepiece, eyepiece)

    def test_create_observations_nagetives(self) -> None:
        date = datetime.datetime(2013, 12, 1).date()
        location = Location.create(
            name="Horsens",
            country="Denmark",
            latitude="55:51:38",
            longitude="-9:51:1",
            altitude=0,
        )
        session = Session.create(date=date, location=location)
        betelgeuse = Object.create(name="Betelgeuse")
        telescope = Telescope.create(
            name="Explorer 150P", aperture=150, focal_length=750
        )
        eyepiece = EyePiece.create(type="Plössl", focal_length=6, width=1.25)
        optic_filter = Filter.create(name="Moon filter")
        binocular = Binocular.create(name="Something", aperture=50, magnification=12)

        # Telescope and binocular
        with self.assertRaises(ValueError):
            api.create_observation(
                session, betelgeuse, telescope=telescope, binocular=binocular
            )

        # Binocular with eyepiece
        with self.assertRaises(ValueError):
            api.create_observation(
                session, betelgeuse, binocular=binocular, eyepiece=eyepiece
            )

        # Binocular with eyepiece
        with self.assertRaises(ValueError):
            api.create_observation(
                session, betelgeuse, binocular=binocular, optic_filter=optic_filter
            )

        # Telescope and not eyepiece
        with self.assertRaises(ValueError):
            api.create_observation(session, betelgeuse, telescope=telescope)

    def test_delete_location_without_session(self) -> None:
        location = Location.create(
            name="Horsens",
            country="Denmark",
            latitude="55:51:38",
            longitude="-9:51:1",
            altitude=0,
        )
        deleted = api.delete_location(location)
        self.assertTrue(deleted)
        self.assertIsNone(Location.get_or_none(1))

    def test_delete_location_with_session(self) -> None:
        date = datetime.datetime(2013, 12, 1).date()
        location = Location.create(
            name="Horsens",
            country="Denmark",
            latitude="55:51:38",
            longitude="-9:51:1",
            altitude=0,
        )
        Session.create(date=date, location=location)
        deleted = api.delete_location(location)
        self.assertFalse(deleted)
        self.assertIsNotNone(Location.get_or_none(1))
        self.assertIsNotNone(Session.get_or_none(1))

    def test_get_monthly_report(self) -> None:
        telescope = Telescope.create(
            name="Explorer 150P", aperture=150, focal_length=750
        )
        eyepiece = EyePiece.create(type="Plössl", focal_length=6, width=1.25)

        date1 = datetime.datetime(2013, 12, 1).date()
        date2 = datetime.datetime(2013, 12, 5).date()
        date3 = datetime.datetime(2013, 12, 9).date()
        location = Location.create(
            name="Horsens",
            country="Denmark",
            latitude="55:51:38",
            longitude="-9:51:1",
            altitude=0,
        )
        session1 = Session.create(date=date1, location=location)
        session2 = Session.create(date=date2, location=location)
        session3 = Session.create(date=date3, location=location)
        sessions = (session1, session2, session3)

        objects = (
            Object.create(name="arcturus"),
            Object.create(name="betelgeuse"),
            Object.create(name="capella"),
            Object.create(name="M31"),
            Object.create(name="M42"),
            Object.create(name="M81"),
        )

        # Create observations
        unique_objects = set()
        object_observations: dict[Object, int] = dict()
        n_observations = 0
        for session in sessions:
            for obj in objects:
                if random.random() > 0.5:
                    unique_objects.add(obj)
                    if obj in object_observations.keys():
                        object_observations[obj] += 1
                    else:
                        object_observations[obj] = 1
                    n_observations += 1
                    api.create_observation(
                        session,
                        obj,
                        telescope=telescope,
                        eyepiece=eyepiece,
                    )

        most_observed_objects = set(
            obj
            for obj, obs in object_observations.items()
            if obs == max(object_observations.values())
        )

        empty_report = api.get_monthly_report(2013, 11)
        self.assertIsNone(empty_report)

        report = api.get_monthly_report(2013, 12)
        self.assertIsNotNone(report)
        self.assertIsInstance(report, Report)
        if report:
            self.assertEqual(report.n_sessions, len(sessions))
            self.assertEqual(report.n_observations, n_observations)
            self.assertEqual(
                report.unique_objects, sorted(unique_objects, key=lambda x: x.name)
            )
            self.assertEqual(
                report.most_observed_objects,
                sorted(most_observed_objects, key=lambda x: x.name),
            )

    def test_get_yearly_report(self) -> None:
        """Same implementation as above, but simpler query"""
        pass
