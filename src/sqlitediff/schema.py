from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Dict, List, NewType, Optional, Set

from .diff import SchemaDiff, schema_diff
from .parser import TableTransformer, create_table_parser

ColumnOption = NewType("ColumnOption", str)
TableConstraint = NewType("TableConstraint", str)
TableOption = NewType("TableOption", str)


@dataclass(unsafe_hash=True)
class Column:
    name: str
    type: Optional[str]
    constraints: Set[ColumnOption] = field(hash=False)


@dataclass
class Table:
    name: str
    columns: Dict[str, Column]
    constraints: Set[TableConstraint]
    options: Set[TableOption]


Index = NewType("Index", str)
View = NewType("View", str)
Trigger = NewType("Trigger", str)


@dataclass
class Schema:
    tables: Dict[str, Table]
    indices: Dict[str, Index]
    views: Dict[str, View]
    triggers: Dict[str, Trigger]

    def difference(self, other: Schema) -> SchemaDiff:
        return schema_diff(self, other)


def load_tables(sql: str) -> List[Table]:
    tree = create_table_parser().parse(sql)
    return TableTransformer().transform(tree).children


def load_schema(conn: sqlite3.Connection) -> Schema:
    tables = conn.execute("SELECT name, sql FROM sqlite_schema WHERE type = 'table'").fetchall()
    indices = conn.execute("SELECT name, sql FROM sqlite_schema WHERE type = 'index'").fetchall()
    views = conn.execute("SELECT name, sql FROM sqlite_schema WHERE type = 'view'").fetchall()
    triggers = conn.execute("SELECT name, sql FROM sqlite_schema WHERE type = 'trigger'").fetchall()
    return Schema(
        tables={name: load_tables(sql)[0] for name, sql in tables},
        indices={name: Index(sql) for name, sql in indices},
        views={name: View(sql) for name, sql in views},
        triggers={name: Trigger(sql) for name, sql in triggers},
    )
