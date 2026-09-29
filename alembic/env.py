import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, text
from alembic import context
from geoalchemy2 import alembic_helpers

# Append project root to sys.path so app imports work inside the container
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.db.base import Base  # noqa: F401 – registers all models on Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Dynamically override sqlalchemy.url from app settings (works inside Docker)
config.set_main_option("sqlalchemy.url", settings.SQLALCHEMY_DATABASE_URI)

target_metadata = Base.metadata

# --- Schemas and tables that belong to PostGIS / Tiger geocoder. ---
# These are bundled with postgis/postgis Docker image and must NEVER be
# included in our application migrations.
_EXCLUDED_SCHEMAS = {"tiger", "tiger_data", "topology"}

_EXCLUDED_TABLES = {
    # PostGIS spatial meta-tables
    "spatial_ref_sys",
    "geometry_columns",
    "geography_columns",
    "raster_columns",
    "raster_overviews",
}


def include_object(object, name, type_, reflected, compare_to):
    """Return True only for objects that belong to our application schema."""
    # Exclude entire non-public schemas (tiger, tiger_data, topology)
    if hasattr(object, "schema") and object.schema in _EXCLUDED_SCHEMAS:
        return False
    if type_ == "table":
        # Exclude PostGIS system tables in public schema
        if name in _EXCLUDED_TABLES:
            return False
        # Exclude Tiger / topology tables that may land in public schema
        if reflected and compare_to is None:
            # This is a reflected table not in our metadata → ignore it
            return False
    return alembic_helpers.include_object(object, name, type_, reflected, compare_to)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        include_schemas=False,
        render_item=alembic_helpers.render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            include_schemas=False,
            render_item=alembic_helpers.render_item,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()