from functools import lru_cache

from arango import ArangoClient
from arango.database import StandardDatabase
from django.conf import settings


@lru_cache()
def arango_client():
    return ArangoClient(hosts=settings.MULTINET_ARANGO_URL)


def db(name: str):
    return arango_client().db(name, username='root', password=settings.MULTINET_ARANGO_PASSWORD)


@lru_cache()
def arango_system_db():
    return db('_system')


def ensure_db_created(name: str) -> None:
    sysdb = arango_system_db()
    if not sysdb.has_database(name):
        sysdb.create_database(name)


def ensure_db_deleted(name: str) -> None:
    sysdb = arango_system_db()
    if sysdb.has_database(name):
        sysdb.delete_database(name)


def get_or_create_db(name: str) -> StandardDatabase:
    ensure_db_created(name)
    return db(name)
