"""Dialect-portable column types (PostgreSQL production + SQLite local smoke)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, SmallInteger, TypeDecorator, Uuid
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID


class GUID(TypeDecorator):
    """UUID that uses native PG UUID and generic Uuid elsewhere."""

    impl = Uuid
    cache_ok = True

    def load_dialect_impl(self, dialect):  # type: ignore[no-untyped-def]
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(Uuid(as_uuid=True))


class JSONDoc(TypeDecorator):
    """JSONB on PostgreSQL, JSON elsewhere."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):  # type: ignore[no-untyped-def]
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class IntArray(TypeDecorator):
    """SmallInteger[] on PostgreSQL, JSON list elsewhere."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):  # type: ignore[no-untyped-def]
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(SmallInteger()))
        return dialect.type_descriptor(JSON())

    def process_result_value(self, value: Any, dialect) -> list[int] | None:  # type: ignore[no-untyped-def]
        if value is None:
            return None
        return [int(x) for x in value]
