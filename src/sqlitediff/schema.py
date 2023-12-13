from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Dict, List, NewType, Optional, Set, cast

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

    def to_sql(self) -> str:
        parts = [self.name]
        if self.type is not None:
            parts.append(self.type)
        parts.extend(self.constraints)
        return " ".join(parts)


@dataclass
class Table:
    name: str
    columns: Dict[str, Column]
    constraints: Set[TableConstraint]
    options: Set[TableOption]
    sql: Optional[str] = field(default=None, repr=False)


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


def load_tables(sql: str, *, only_one: bool = False) -> List[Table]:
    tree = create_table_parser().parse(sql)
    tables = cast(List[Table], TableTransformer().transform(tree).children)

    if only_one and len(tables) != 1:
        raise ValueError(f"Expected exactly 1 table definition, found {len(tables)}")

    for table in tables:
        table.sql = sql

    return tables


def load_schema(conn: sqlite3.Connection) -> Schema:
    # fmt: off
    tables   = conn.execute("SELECT name, sql FROM sqlite_schema WHERE type =   'table'").fetchall()
    indices  = conn.execute("SELECT name, sql FROM sqlite_schema WHERE type =   'index'").fetchall()
    views    = conn.execute("SELECT name, sql FROM sqlite_schema WHERE type =    'view'").fetchall()
    triggers = conn.execute("SELECT name, sql FROM sqlite_schema WHERE type = 'trigger'").fetchall()
    # fmt: on
    return Schema(
        tables={name: load_tables(sql, only_one=True)[0] for name, sql in tables},
        indices={name: Index(sql) for name, sql in indices},
        views={name: View(sql) for name, sql in views},
        triggers={name: Trigger(sql) for name, sql in triggers},
    )
