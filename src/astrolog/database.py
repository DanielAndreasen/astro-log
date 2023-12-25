import os
from typing import Iterable, Optional, cast

import astropy.units as u
from astropy.coordinates import EarthLocation
from peewee import (
    AutoField,
    BlobField,
    BooleanField,
    Check,
    DatabaseProxy,
    DateField,
    FloatField,
    ForeignKeyField,
    IntegerField,
    Model,
    TextField,
)

database_proxy = DatabaseProxy()
degree = cast(u.UnitBase, u.deg)
meter = cast(u.UnitBase, u.m)


class AstroLogModel(Model):
    id = AutoField()

    class Meta:
        database = database_proxy


class Location(AstroLogModel):
    name = TextField()
    country = TextField()
    latitude = TextField()
    longitude = TextField()
    utcoffset = IntegerField(default=0)
    altitude = IntegerField()

    @staticmethod
    def coordinate_to_decimal(coordinate: str) -> float:
        parts = [int(part) for part in coordinate.split(":")]
        if parts[0] < 0:
            return parts[0] - parts[1] / 60 - parts[2] / 3600
        return parts[0] + parts[1] / 60 + parts[2] / 3600

    @property
    def earth_location(self) -> EarthLocation:
        latitude_decimal = Location.coordinate_to_decimal(str(self.latitude))
        longitude_decimal = Location.coordinate_to_decimal(str(self.longitude))
        return EarthLocation(
            lat=latitude_decimal * degree,
            lon=longitude_decimal * degree,
            height=self.altitude * meter,
        )


class Filter(AstroLogModel):
    name = TextField()


class FrontFilter(AstroLogModel):
    name = TextField()


class EyePiece(AstroLogModel):
    type = TextField()
    focal_length = IntegerField()
    width = FloatField()
    afov = IntegerField(null=True, default=None)

    def use_filter(self, optic_filter: Filter) -> None:
        self.optic_filter_ = optic_filter

    @property
    def optic_filter(self) -> Optional[Filter]:
        if "optic_filter_" in self.__dict__.keys():
            return self.optic_filter_
        return None


class Barlow(AstroLogModel):
    name = TextField()
    multiplier = IntegerField()


class Binocular(AstroLogModel):
    name = TextField()
    aperture = IntegerField()
    magnification = IntegerField()


class Camera(AstroLogModel):
    manufacture = TextField()
    model = TextField()
    megapixel = FloatField()


class Telescope(AstroLogModel):
    _eyepiece = _front_filter = _barlow = _camera = None

    name = TextField()
    aperture = IntegerField()
    focal_length = IntegerField()

    @property
    def f_ratio(self) -> float:
        return self.focal_length / self.aperture

    @property
    def magnification(self) -> Optional[int]:
        if eyepiece := self.eyepiece:
            if barlow := self.barlow:
                return int(
                    self.focal_length / eyepiece.focal_length * barlow.multiplier
                )
            return int(self.focal_length / eyepiece.focal_length)
        return None

    @property
    def fov(self) -> float | None:
        """True field of view, which is apparent fov (afov) / magnification"""
        if eyepiece := self.eyepiece:
            if eyepiece.afov:
                return round(
                    eyepiece.afov / (self.focal_length / eyepiece.focal_length), 2
                )
        return None

    @property
    def eyepiece(self) -> Optional[EyePiece]:
        return self._eyepiece

    @property
    def front_filter(self) -> Optional[FrontFilter]:
        return self._front_filter

    @property
    def barlow(self) -> Optional[Barlow]:
        return self._barlow

    @property
    def camera(self) -> Optional[Camera]:
        return self._camera

    def use_eyepiece(self, eyepiece: EyePiece) -> None:
        self._camera = None
        self._eyepiece = eyepiece

    def use_barlow(self, barlow: Barlow) -> None:
        self._barlow = barlow

    def attach_front_filter(self, front_filter: FrontFilter) -> None:
        self._front_filter = front_filter

    def use_camera(self, camera: Camera) -> None:
        self._barlow = self._eyepiece = None
        self._camera = camera


class Structure(AstroLogModel):
    name = TextField()

    def add_object(self, object: "Object") -> None:
        if structure := object.structure:
            raise ValueError(f'Already part of "{structure.name}"')
        object.structure = self
        object.save()

    @property
    def objects(self) -> list["Object"]:
        return list(Object.select().join(Structure).where(Structure.name == self.name))

    @property
    def objects_str(self) -> str:
        return ", ".join([str(obj.name) for obj in self.objects])


class Kind(AstroLogModel):
    name = TextField()


class Object(AstroLogModel):
    name = TextField()
    favourite = BooleanField(default=False)
    to_be_watched: BooleanField | bool = BooleanField(default=False)
    structure: ForeignKeyField | Structure = ForeignKeyField(Structure, null=True)
    kind: ForeignKeyField | Kind = ForeignKeyField(Kind, null=True)

    def toggle_favourite(self) -> None:
        self.favourite = not self.favourite
        self.save()

    @property
    def alt_names(self) -> list[str | None]:
        query = AltName.select().join(Object).where(Object.id == self.id)
        return [alt.name for alt in query]


class AltName(AstroLogModel):
    object = ForeignKeyField(Object)
    name = TextField(unique=True)


class Condition(AstroLogModel):
    temperature = IntegerField()
    humidity = IntegerField(
        null=True, constraints=[Check("humidity >= 0"), Check("humidity <= 100")]
    )
    seeing = FloatField(null=True)


class Session(AstroLogModel):
    date = DateField()
    location = ForeignKeyField(Location)
    moon_phase = IntegerField(
        null=True, constraints=[Check("moon_phase >= 0"), Check("moon_phase <= 100")]
    )
    condition = ForeignKeyField(Condition, null=True)
    note = TextField(null=True)

    @property
    def observations(self) -> Iterable["Observation"]:
        query = Observation.select().join(Session).where(Session.id == self.id)
        for observation in query:
            yield observation

    @property
    def number_of_observations(self) -> int:
        return len(Observation.select().join(Session).where(Session.id == self.id))


class Image(AstroLogModel):
    fname = TextField()

    @property
    def image_loc(self) -> str:
        return os.path.join("/static/uploads", str(self.fname))

    @property
    def observation(self) -> "Observation":
        return Observation.get(image=self)


class Observation(AstroLogModel):
    object = ForeignKeyField(Object)
    session = ForeignKeyField(Session)
    binocular = ForeignKeyField(Binocular, null=True)
    telescope = ForeignKeyField(Telescope, null=True)
    eyepiece = ForeignKeyField(EyePiece, null=True)
    barlow = ForeignKeyField(Barlow, null=True)
    camera = ForeignKeyField(Camera, null=True)
    front_filter = ForeignKeyField(FrontFilter, null=True)
    optic_filter = ForeignKeyField(Filter, null=True)
    note = TextField(null=True)
    image = ForeignKeyField(Image, null=True)

    @property
    def magnification(self) -> Optional[int]:
        if self.telescope:
            self.telescope.use_eyepiece(self.eyepiece)
            if self.barlow:
                self.telescope.use_barlow(self.barlow)
            return self.telescope.magnification
        elif self.binocular:
            return self.binocular.magnification
        return None

    @property
    def fov(self) -> Optional[float]:
        if not self.telescope:
            return None
        if not self.eyepiece:
            return None
        if not self.eyepiece.afov:
            return None
        self.telescope.use_eyepiece(self.eyepiece)
        if self.barlow:
            self.telescope.use_barlow(self.barlow)
        return self.telescope.fov

    @property
    def naked_eye(self) -> bool:
        return not self.telescope and not self.binocular

    def add_image(self, path: str) -> None:
        fname = os.path.basename(path)
        image = Image.create(fname=fname)
        self.image = image
        self.save()


class User(AstroLogModel):
    username = TextField()
    hashed_password = BlobField()


MODELS = [
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
    User,
]
