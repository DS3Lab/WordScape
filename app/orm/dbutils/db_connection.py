from logging.config import fileConfig

from sqlalchemy import create_engine, Engine
from sqlalchemy import pool
import settings
import configparser


def connect_to_db() -> Engine:
    config = configparser.ConfigParser()
    config.read(settings.filesystem.ALEMBIC_INI_LOC)
    key = config.get('alembic', 'sqlalchemy.url')
    engine = create_engine(key)
    return engine

