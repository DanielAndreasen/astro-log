import datetime
from unittest import TestCase

from astropy.coordinates import EarthLocation
from peewee import IntegrityError, SqliteDatabase

from astrolog.database import (
    MODELS,
    AltName,
    Barlow,
    Binocular,
    Camera,
    Condition,
    EyePiece,
    Filter,
    FrontFilter,
    Image,
    Kind,
    Location,
    Object,
    Observation,
    Session,
    Structure,
    Telescope,
    database_proxy,
)

db = SqliteDatabase(":memory:")
database_proxy.initialize(db)
db.create_tables(MODELS)


def get_telescope(name: str, aperture: int, focal_length: int) -> Telescope:
    telescope, _ = Telescope.get_or_create(
        name=name, aperture=aperture, focal_length=focal_length
    )
    return telescope


def get_binocular(name: str, aperture: int, magnification: int) -> Binocular:
    binocular, _ = Binocular.get_or_create(
        name=name, aperture=aperture, magnification=magnification
    )
    return binocular


def get_condition(
    temperature: int, humidity: int, seeing: float | None = None
) -> Condition:
    condition = Condition.create(
        temperature=temperature, humidity=humidity, seeing=seeing
    )
    return condition


def get_filter(name: str) -> Filter:
    filter, _ = Filter.get_or_create(name=name)
    return filter


def get_front_filter(name: str) -> FrontFilter:
    filter, _ = FrontFilter.get_or_create(name=name)
    return filter


def get_eyepiece(
    type: str, focal_length: int, width: float, afov: int | None = None
) -> EyePiece:
    eyepiece, _ = EyePiece.get_or_create(
        type=type, focal_length=focal_length, width=width, afov=afov
    )
    return eyepiece


def get_camera(manufacture: str, model: str, megapixel: float) -> Camera:
    camera, _ = Camera.get_or_create(
        manufacture=manufacture, model=model, megapixel=megapixel
    )
    return camera


def get_barlow(name: str, multiplier: int) -> Barlow:
    barlow, _ = Barlow.get_or_create(name=name, multiplier=multiplier)
    return barlow


def get_kind(name: str) -> Kind:
    kind, _ = Kind.get_or_create(name=name)
    return kind


def get_object(
    name: str,
    favourite: bool = False,
    to_be_watched: bool = False,
    kind: None | Kind = None,
) -> Object:
    object, _ = Object.get_or_create(
        name=name, kind=kind, favourite=favourite, to_be_watched=to_be_watched
    )
    return object


def get_location(
    name: str,
    country: str,
    latitude: str,
    longitude: str,
    utcoffset: int,
    altitude: int,
) -> Location:
    location, _ = Location.get_or_create(
        name=name,
        country=country,
        latitude=latitude,
        longitude=longitude,
        utcoffset=utcoffset,
        altitude=altitude,
    )
    return location


def set_alt_name(object: Object, name: str) -> None:
    AltName.create(object=object, name=name)


def get_structure(name: str) -> Structure:
    structure, _ = Structure.get_or_create(name=name)
    return structure


class TestDB(TestCase):
    def setUp(self) -> None:
        db.create_tables(MODELS)

    def tearDown(self) -> None:
        db.drop_tables(MODELS)

    def test_filter(self) -> None:
        moon_filter = get_filter(name="Moon filter")
        self.assertEqual(moon_filter.name, "Moon filter")

    def test_eyepiece(self) -> None:
        plossl = get_eyepiece(type="Plössl", focal_length=6, width=1.25)
        self.assertEqual(plossl.type, "Plössl")
        self.assertEqual(plossl.focal_length, 6)
        self.assertEqual(plossl.width, 1.25)
        self.assertEqual(plossl.optic_filter, None)
        # Insert filter
        moon_filter = get_filter(name="Moon filter")
        plossl.use_filter(moon_filter)
        self.assertEqual(plossl.optic_filter, moon_filter)
        if plossl.optic_filter:
            self.assertEqual(plossl.optic_filter.name, "Moon filter")
        # Change filter
        red_filter = get_filter(name="Red filter")
        plossl.use_filter(red_filter)
        self.assertEqual(plossl.optic_filter, red_filter)

    def test_camera(self) -> None:
        bresser = get_camera(
            manufacture="Bresser", model="HD moon, planet, and guiding", megapixel=1.2
        )
        self.assertEqual(bresser.manufacture, "Bresser")
        self.assertEqual(bresser.model, "HD moon, planet, and guiding")
        self.assertEqual(bresser.megapixel, 1.2)

    def test_binocular(self) -> None:
        binocular = get_binocular(name="Something", aperture=50, magnification=12)
        self.assertEqual(binocular.name, "Something")
        self.assertEqual(binocular.aperture, 50)
        self.assertEqual(binocular.magnification, 12)

    def test_telescope(self) -> None:
        telescope = get_telescope(name="Explorer 150P", aperture=150, focal_length=750)
        self.assertEqual(telescope.name, "Explorer 150P")
        self.assertEqual(telescope.aperture, 150)
        self.assertEqual(telescope.focal_length, 750)
        self.assertEqual(telescope.f_ratio, 750 / 150)
        self.assertEqual(telescope.magnification, None)
        self.assertEqual(telescope.front_filter, None)
        self.assertEqual(telescope.barlow, None)
        self.assertEqual(telescope.camera, None)
        # Use one eyepiece
        plossl = get_eyepiece(type="Plössl", focal_length=6, width=1.25, afov=60)
        magnification1 = telescope.focal_length / plossl.focal_length
        fov = plossl.afov / (telescope.focal_length / plossl.focal_length)
        telescope.use_eyepiece(plossl)
        self.assertEqual(telescope.magnification, magnification1)
        self.assertEqual(telescope.fov, fov)
        # Use barlow
        barlow = get_barlow(name="barlow", multiplier=2)
        telescope.use_barlow(barlow)
        magnification2 = (
            telescope.focal_length / plossl.focal_length * barlow.multiplier
        )
        self.assertEqual(telescope.barlow, barlow)
        self.assertEqual(telescope.magnification, magnification2)
        # Change eyepiece
        kellner = get_eyepiece(type="Kellner", focal_length=15, width=1.25)
        magnification3 = (
            telescope.focal_length / kellner.focal_length * barlow.multiplier
        )
        telescope.use_eyepiece(kellner)
        self.assertEqual(telescope.magnification, magnification3)
        # Use a filter in front (solar white filter)
        solar_filter = get_front_filter(name="Solar front filter")
        telescope.attach_front_filter(solar_filter)
        self.assertEqual(telescope.front_filter, solar_filter)
        # Use a decicated camera
        bresser = get_camera(
            manufacture="Bresser", model="HD moon, planet, and guiding", megapixel=1.2
        )
        self.assertIsNotNone(telescope.eyepiece)
        self.assertIsNotNone(telescope.barlow)
        telescope.use_camera(bresser)
        self.assertIsNone(telescope.eyepiece)
        self.assertIsNone(telescope.barlow)
        self.assertEqual(telescope.camera, bresser)
        # Change back to an eyepiece
        telescope.use_eyepiece(plossl)
        self.assertIsNone(telescope.camera)
        self.assertIsNotNone(telescope.eyepiece)

    def test_location(self) -> None:
        horsens = get_location(
            name="Horsens",
            country="Denmark",
            latitude="55:51:38",
            longitude="-9:51:1",
            utcoffset=2,
            altitude=0,
        )
        self.assertEqual(horsens.name, "Horsens")
        self.assertEqual(horsens.country, "Denmark")
        self.assertEqual(horsens.latitude, "55:51:38")
        self.assertEqual(horsens.longitude, "-9:51:1")
        self.assertEqual(horsens.utcoffset, 2)
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
        horsens = get_location(
            name="Horsens",
            country="Denmark",
            latitude="55:51:38",
            longitude="-9:51:1",
            utcoffset=2,
            altitude=0,
        )
        september_13_1989 = datetime.datetime(1989, 9, 13).date()
        session, _ = Session.get_or_create(date=september_13_1989, location=horsens)
        self.assertEqual(session.date, september_13_1989)
        self.assertEqual(session.location, horsens)
        self.assertEqual(len(session.observation_set), 0)
        self.assertEqual(session.moon_phase, None)
        self.assertEqual(session.condition, None)
        self.assertEqual(session.number_of_observations, 0)
        self.assertEqual(session.note, None)

    def test_session_with_moon_phases(self) -> None:
        horsens = get_location(
            name="Horsens",
            country="Denmark",
            latitude="55:51:38",
            longitude="-9:51:1",
            utcoffset=2,
            altitude=0,
        )
        september_13_1989 = datetime.datetime(1989, 9, 13).date()
        condition = get_condition(temperature=-2, humidity=65, seeing=1.2)
        session, _ = Session.get_or_create(
            date=september_13_1989, location=horsens, condition=condition
        )
        self.assertEqual(session.condition, condition)

    def test_session_with_condition(self) -> None:
        horsens = get_location(
            name="Horsens",
            country="Denmark",
            latitude="55:51:38",
            longitude="-9:51:1",
            utcoffset=2,
            altitude=0,
        )
        september_13_1989 = datetime.datetime(1989, 9, 13).date()
        session, _ = Session.get_or_create(
            date=september_13_1989, location=horsens, moon_phase=86
        )
        self.assertEqual(session.moon_phase, 86)
        # Too high moon_phase
        with self.assertRaises(IntegrityError):
            session, _ = Session.get_or_create(
                date=september_13_1989, location=horsens, moon_phase=101
            )
        # Too low moon_phase
        with self.assertRaises(IntegrityError):
            session, _ = Session.get_or_create(
                date=september_13_1989, location=horsens, moon_phase=-1
            )

    def test_session_with_note(self) -> None:
        horsens = get_location(
            name="Horsens",
            country="Denmark",
            latitude="55:51:38",
            longitude="-9:51:1",
            utcoffset=2,
            altitude=0,
        )
        september_13_1989 = datetime.datetime(1989, 9, 13).date()
        session, _ = Session.get_or_create(
            date=september_13_1989, location=horsens, note="this is a note"
        )
        self.assertEqual(session.note, "this is a note")

    def test_kind(self) -> None:
        stellar = get_kind(name="Stellar")
        self.assertEqual(stellar.name, "Stellar")

    def test_object(self) -> None:
        arcturus = get_object(name="Arcturus")
        self.assertEqual(arcturus.name, "Arcturus")
        self.assertFalse(arcturus.favourite)
        self.assertFalse(arcturus.to_be_watched)
        self.assertIsNone(arcturus.kind)
        stellar = get_kind(name="Stellar")
        betelgeuse = get_object(
            name="Betelgeuse", kind=stellar, favourite=True, to_be_watched=True
        )
        self.assertEqual(betelgeuse.name, "Betelgeuse")
        self.assertTrue(betelgeuse.favourite)
        self.assertTrue(betelgeuse.to_be_watched)
        self.assertTrue(betelgeuse.kind, stellar)
        arcturus.toggle_favourite()
        arcturus = Object.get(name="Arcturus")
        self.assertTrue(arcturus.favourite)

    def test_object_alt_names(self) -> None:
        arcturus = get_object(name="Arcturus")
        self.assertListEqual(arcturus.alt_names, [])
        set_alt_name(arcturus, "HD 124897")
        set_alt_name(arcturus, "HIP 69673")
        self.assertIsInstance(arcturus.alt_names, list)
        self.assertEqual(len(arcturus.alt_names), 2)
        self.assertIn("HD 124897", arcturus.alt_names)
        self.assertIn("HIP 69673", arcturus.alt_names)

    def test_structures_of_objects(self) -> None:
        alnitak = get_object(name="Alnitak")
        alnilam = get_object(name="Alnilam")
        mintaka = get_object(name="Mintaka")
        belt = get_structure(name="Orion's belt")
        self.assertIsInstance(belt, Structure)
        self.assertListEqual(belt.objects, [])
        belt.add_object(alnitak)
        self.assertListEqual(belt.objects, [alnitak])
        belt.add_object(alnilam)
        belt.add_object(mintaka)
        self.assertIn(alnitak, belt.objects)
        self.assertIn(alnilam, belt.objects)
        self.assertIn(mintaka, belt.objects)
        orion = get_structure(name="Orion")
        with self.assertRaises(ValueError):
            orion.add_object(alnilam)

    def test_observation_with_binocular(self) -> None:
        binocular = get_binocular(name="Something", aperture=50, magnification=12)
        horsens = get_location(
            name="Horsens",
            country="Denmark",
            latitude="55:51:38",
            longitude="-9:51:1",
            utcoffset=2,
            altitude=0,
        )
        september_13_1989 = datetime.datetime(1989, 9, 13).date()
        session, _ = Session.get_or_create(date=september_13_1989, location=horsens)
        betelgeuse = get_object(name="Betelgeuse")
        observation, _ = Observation.get_or_create(
            object=betelgeuse, session=session, binocular=binocular
        )

        self.assertIsNone(observation.note)
        self.assertEqual(observation.session, session)
        self.assertEqual(observation.object, betelgeuse)
        self.assertEqual(observation.binocular, binocular)

    def test_observation_with_telescope(self) -> None:
        plossl = get_eyepiece(type="Plössl", focal_length=6, width=1.25)
        moon_filter = get_filter(name="Moon filter")
        solar_filter = get_front_filter(name="Solar filter")
        barlow = get_barlow(name="Barlow", multiplier=2)
        bresser = get_camera(
            manufacture="Bresser", model="HD moon, planet, and guiding", megapixel=1.2
        )
        telescope = get_telescope(name="Explorer 150P", aperture=150, focal_length=750)
        telescope.use_eyepiece(plossl)
        telescope.use_barlow(barlow)
        telescope.attach_front_filter(solar_filter)
        magnification = telescope.magnification

        horsens = get_location(
            name="Horsens",
            country="Denmark",
            latitude="55:51:38",
            longitude="-9:51:1",
            utcoffset=2,
            altitude=0,
        )
        september_13_1989 = datetime.datetime(1989, 9, 13).date()
        session, _ = Session.get_or_create(date=september_13_1989, location=horsens)

        betelgeuse = get_object(name="Betelgeuse")

        observation = Observation(
            object=betelgeuse,
            session=session,
            telescope=telescope,
            eyepiece=plossl,
            barlow=barlow,
            optic_filter=moon_filter,
            front_filter=solar_filter,
        )
        observation.save()
        self.assertEqual(observation.note, None)
        self.assertEqual(observation.camera, None)
        self.assertEqual(observation.session, session)
        self.assertEqual(observation.object, betelgeuse)
        self.assertEqual(observation.eyepiece, plossl)
        self.assertEqual(observation.barlow, barlow)
        self.assertEqual(observation.optic_filter, moon_filter)
        self.assertEqual(observation.front_filter, solar_filter)
        self.assertEqual(observation.telescope, telescope)
        self.assertEqual(observation.magnification, magnification)

        observation = Observation(
            object=betelgeuse,
            session=session,
            telescope=telescope,
            eyepiece=plossl,
            note="Wow, what a view tonight!",
        )
        observation.save()
        self.assertEqual(observation.optic_filter, None)
        self.assertEqual(observation.note, "Wow, what a view tonight!")
        self.assertEqual(session.number_of_observations, 2)

        observation = Observation(
            object=betelgeuse,
            session=session,
            telescope=telescope,
            camera=bresser,
            note="First time with a dedicated camera",
        )
        self.assertIsNone(observation.eyepiece)
        self.assertEqual(observation.camera, bresser)

    def test_observation_add_image(self) -> None:
        horsens = get_location(
            name="Horsens",
            country="Denmark",
            latitude="55:51:38",
            longitude="-9:51:1",
            utcoffset=2,
            altitude=0,
        )
        september_13_1989 = datetime.datetime(1989, 9, 13).date()
        session, _ = Session.get_or_create(date=september_13_1989, location=horsens)
        betelgeuse = get_object(name="Betelgeuse")
        observation = Observation(object=betelgeuse, session=session)
        observation.save()
        self.assertIsNone(observation.image)
        observation.add_image("resources/test/M42.png")
        image = observation.image
        self.assertIsNotNone(image)
        self.assertIsInstance(image, Image)
        self.assertEqual(image.fname, "M42.png")
        self.assertEqual(image.image_loc, "/static/uploads/M42.png")

    def test_session_with_observations(self) -> None:
        plossl = get_eyepiece(type="Plössl", focal_length=6, width=1.25)
        kellner = get_eyepiece(type="Kellner", focal_length=15, width=1.25)
        telescope = get_telescope(name="Explorer 150P", aperture=150, focal_length=750)

        horsens = get_location(
            name="Horsens",
            country="Denmark",
            latitude="55:51:38",
            longitude="-9:51:1",
            utcoffset=2,
            altitude=0,
        )
        september_13_1989 = datetime.datetime(1989, 9, 13).date()
        session, _ = Session.get_or_create(date=september_13_1989, location=horsens)

        arcturus = get_object(name="Arcturus")
        betelgeuse = get_object(name="Betelgeuse")

        Observation.get_or_create(
            object=betelgeuse, session=session, telescope=telescope, eyepiece=plossl
        )
        Observation.get_or_create(
            object=arcturus, session=session, telescope=telescope, eyepiece=kellner
        )

        self.assertEqual(len(session.observation_set), 2)
        for observation in session.observations:
            self.assertIsNotNone(observation.object)

    def test_location_EarthLocation(self) -> None:
        horsens = get_location(
            name="Horsens",
            country="Denmark",
            latitude="55:51:38",
            longitude="-9:51:1",
            utcoffset=2,
            altitude=0,
        )
        earth_location = horsens.earth_location
        self.assertIsInstance(earth_location, EarthLocation)
