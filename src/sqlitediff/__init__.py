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
    ColumnOption,
    Index,
    Schema,
    Table,
    TableConstraint,
    TableOption,
    Trigger,
    View,
    load_schema,
)

__version__ = "0.1.2"
