import os

from peewee import IntegerField, SqliteDatabase
from playhouse.migrate import SqliteMigrator, migrate

from astrolog.database import database_proxy

DEFAULT_DB = os.path.join(os.path.abspath("."), "AstroLog.db")
ASTRO_LOG_DB = os.getenv("ASTRO_LOG_DB", DEFAULT_DB)
db = SqliteDatabase(ASTRO_LOG_DB)
database_proxy.initialize(db)
migrator = SqliteMigrator(db)

fov = IntegerField(null=True, default=None)

with db.transaction():
    migrate(
        migrator.add_column("eyepiece", "fov", fov),
    )
