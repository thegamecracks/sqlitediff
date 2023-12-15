"""
Compares the schemas of two SQLite databases and generates
a simplified SQL script for aiding migrations.
"""
from .diff import (
    Change,
    DeletedColumn,
    DeletedObject,
    DeletedTable,
    ModifiedColumn,
    ModifiedObject,
    ModifiedTable,
    NewColumn,
    NewObject,
    NewTable,
    ObjectType,
    SchemaDiff,
    schema_diff,
)
from .schema import (
    Column,
    ColumnConstraint,
    Index,
    Schema,
    Table,
    TableConstraint,
    TableOption,
    Trigger,
    View,
    load_schema,
)


def _get_version() -> str:
    from importlib.metadata import version

    return version("sqlitediff")


__version__ = _get_version()
