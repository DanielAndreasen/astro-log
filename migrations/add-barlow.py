import os

from peewee import ForeignKeyField, SqliteDatabase
from playhouse.migrate import SqliteMigrator, migrate

from astrolog.database import Barlow, database_proxy

DEFAULT_DB = os.path.join(os.path.abspath("."), "AstroLog.db")
ASTRO_LOG_DB = os.getenv("ASTRO_LOG_DB", DEFAULT_DB)
db = SqliteDatabase(ASTRO_LOG_DB)
database_proxy.initialize(db)
migrator = SqliteMigrator(db)

barlow = ForeignKeyField(Barlow, field=Barlow.id, null=True)

with db.transaction():
    migrate(
        migrator.drop_index("observation", "observation_barlow_id"),
        migrator.add_column("observation", "barlow_id", barlow),
    )
