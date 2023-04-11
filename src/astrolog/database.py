from typing import Iterable, Optional

from peewee import (BlobField, BooleanField, Check, DatabaseProxy, DateField,
                    FloatField, ForeignKeyField, IntegerField, Model,
                    TextField)

database_proxy = DatabaseProxy()


class AstroLogModel(Model):
    class Meta:
        # database = db
        database = database_proxy


class Location(AstroLogModel):
    name = TextField()
    country = TextField()
    latitude = TextField()
    longitude = TextField()
    altitude = IntegerField()


class Filter(AstroLogModel):
    name = TextField()


class EyePiece(AstroLogModel):
    type = TextField()
    focal_length = IntegerField()
    width = FloatField()

    def use_filter(self, optic_filter: Filter) -> None:
        self.optic_filter_ = optic_filter

    @property
    def optic_filter(self) -> Optional[Filter]:
        if 'optic_filter_' in self.__dict__.keys():
            return self.optic_filter_
        return None


class Binocular(AstroLogModel):
    name = TextField()
    aperture = IntegerField()
    magnification = IntegerField()


class Telescope(AstroLogModel):
    name = TextField()
    aperture = IntegerField()
    focal_length = IntegerField()

    @property
    def f_ratio(self) -> float:
        return self.focal_length / self.aperture

    @property
    def magnification(self) -> Optional[int]:
        if 'eyepiece' in self.__dict__.keys():
            return int(self.focal_length / self.eyepiece.focal_length)
        return None

    def use_eyepiece(self, eyepiece: EyePiece) -> None:
        self.eyepiece = eyepiece


class Object(AstroLogModel):
    name = TextField()
    favourite = BooleanField(default=False)
    to_be_watched = BooleanField(default=False)

    def toggle_favourite(self) -> None:
        self.favourite = not self.favourite
        self.save()

    @property
    def alt_names(self) -> None | list[str]:
        return [alt.name for alt in self.altname_set] or None


class AltName(AstroLogModel):
    object = ForeignKeyField(Object)
    name = TextField(unique=True)


class Condition(AstroLogModel):
    temperature = IntegerField()
    humidity = IntegerField(null=True, constraints=[Check('humidity >= 0'), Check('humidity <= 100')])
    seeing = FloatField(null=True)


class Session(AstroLogModel):
    date = DateField()
    location = ForeignKeyField(Location)
    moon_phase = IntegerField(null=True, constraints=[Check('moon_phase >= 0'), Check('moon_phase <= 100')])
    condition = ForeignKeyField(Condition, null=True)

    @property
    def observations(self) -> Iterable['Observation']:
        for observation in self.observation_set:
            yield observation

    @property
    def number_of_observations(self) -> int:
        return len(self.observation_set)


class Observation(AstroLogModel):
    object = ForeignKeyField(Object)
    session = ForeignKeyField(Session)
    binocular = ForeignKeyField(Binocular, null=True)
    telescope = ForeignKeyField(Telescope, null=True)
    eyepiece = ForeignKeyField(EyePiece, null=True)
    optic_filter = ForeignKeyField(Filter, null=True)
    note = TextField(null=True)

    @property
    def magnification(self) -> Optional[int]:
        if self.telescope:
            self.telescope.use_eyepiece(self.eyepiece)
            return self.telescope.magnification
        elif self.binocular:
            return self.binocular.magnification
        return None

    @property
    def naked_eye(self) -> bool:
        return not self.telescope and not self.binocular


class User(AstroLogModel):
    username = TextField()
    hashed_password = BlobField()


MODELS = [Condition, Binocular, Session, EyePiece,
          Filter, Location, Object, Observation,
          Telescope, User, AltName]
