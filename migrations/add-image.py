import os

from peewee import ForeignKeyField, SqliteDatabase
from playhouse.migrate import SqliteMigrator, migrate

from astrolog.database import Image, database_proxy

DEFAULT_DB = os.path.join(os.path.abspath("."), "AstroLog.db")
ASTRO_LOG_DB = os.getenv("ASTRO_LOG_DB", DEFAULT_DB)
db = SqliteDatabase(ASTRO_LOG_DB)
database_proxy.initialize(db)
migrator = SqliteMigrator(db)

image = ForeignKeyField(Image, field=Image.id, null=True)

with db.transaction():
    migrate(
        migrator.drop_index("observation", "observation_image_id"),
        migrator.add_column("observation", "image_id", image),
    )
