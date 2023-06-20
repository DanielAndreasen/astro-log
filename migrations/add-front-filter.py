import os

from peewee import ForeignKeyField, SqliteDatabase
from playhouse.migrate import SqliteMigrator, migrate

from astrolog.database import FrontFilter, database_proxy

DEFAULT_DB = os.path.join(os.path.abspath("."), "AstroLog.db")
ASTRO_LOG_DB = os.getenv("ASTRO_LOG_DB", DEFAULT_DB)
db = SqliteDatabase(ASTRO_LOG_DB)
database_proxy.initialize(db)
migrator = SqliteMigrator(db)

front_filter = ForeignKeyField(FrontFilter, field=FrontFilter.id, null=True)

with db.transaction():
    migrate(
        migrator.drop_index("observation", "observation_front_filter_id"),
        migrator.add_column("observation", "front_filter_id", front_filter),
    )
