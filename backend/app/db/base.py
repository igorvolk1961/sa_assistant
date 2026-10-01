"""Declarative base and shared column helpers."""

import enum

import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def enum_col[E: enum.Enum](py_enum: type[E], name: str) -> sa.Enum:
    """Native PostgreSQL enum that stores the enum *values* (not member names)."""
    return sa.Enum(
        py_enum,
        name=name,
        native_enum=True,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )
