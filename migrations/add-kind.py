import os

from peewee import ForeignKeyField, SqliteDatabase
from playhouse.migrate import SqliteMigrator, migrate

from astrolog.database import Kind, database_proxy

DEFAULT_DB = os.path.join(os.path.abspath("."), "AstroLog.db")
ASTRO_LOG_DB = os.getenv("ASTRO_LOG_DB", DEFAULT_DB)
db = SqliteDatabase(ASTRO_LOG_DB)
database_proxy.initialize(db)
migrator = SqliteMigrator(db)

kind = ForeignKeyField(Kind, field=Kind.id, null=True)

with db.transaction():
    migrate(
        migrator.add_column("object", "kind_id", kind),
    )
