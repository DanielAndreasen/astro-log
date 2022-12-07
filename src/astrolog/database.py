import os
from peewee import FloatField, ForeignKeyField, IntegerField, SqliteDatabase, Model, DateField, TextField
from playhouse.sqlite_ext import SqliteExtDatabase

ASTRO_LOG_DB = os.getenv('ASTRO_LOG_DB', 'AstroLog.db')

if os.getenv('ASTRO_LOG_TEST') == 'true':
    db = SqliteExtDatabase(':memory:')
else:
    db = SqliteDatabase(ASTRO_LOG_DB)


class AstroLogModel(Model):
    class Meta:
        database = db


class Filter(AstroLogModel):
    name = TextField()


class EyePiece(AstroLogModel):
    type = TextField()
    focal_length = IntegerField()
    width = FloatField()

    def use_filter(self, optic_filter: Filter) -> None:
        self.optic_filter_ = optic_filter

    @property
    def optic_filter(self):
        if 'optic_filter_' in self.__dict__.keys():
            return self.optic_filter_
        return None


class Telescope(AstroLogModel):
    name = TextField()
    aperture = IntegerField()
    focal_length = IntegerField()

    @property
    def f_ratio(self):
        return self.focal_length / self.aperture

    @property
    def magnification(self):
        if 'eyepiece' in self.__dict__.keys():
            return self.focal_length / self.eyepiece.focal_length
        return None

    def use_eyepiece(self, eyepiece: EyePiece) -> None:
        self.eyepiece = eyepiece


class Object(AstroLogModel):
    name = TextField()
    magnitude = FloatField()


class Session(AstroLogModel):
    date = DateField()

    @property
    def observations(self):
        for observation in self.observation_set:
            yield observation


class Observation(AstroLogModel):
    object = ForeignKeyField(Object)
    session = ForeignKeyField(Session)
    telescope = ForeignKeyField(Telescope)
    eyepiece = ForeignKeyField(EyePiece)
    optic_filter = ForeignKeyField(Filter, null=True)
    note = TextField(null=True)
    
    @property
    def magnification(self):
        self.telescope.use_eyepiece(self.eyepiece)
        return self.telescope.magnification
