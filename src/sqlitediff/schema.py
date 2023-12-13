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
    raw_name: str
    type: Optional[str]
    constraints: Set[ColumnOption] = field(hash=False)

    def to_sql(self) -> str:
        parts = [self.raw_name]
        if self.type is not None:
            parts.append(self.type)
        parts.extend(self.constraints)
        return " ".join(parts)


@dataclass
class Table:
    name: str
    raw_name: str
    columns: Dict[str, Column]
    constraints: Set[TableConstraint]
    options: Set[TableOption]
    sql: Optional[str] = field(default=None, repr=False)


@dataclass
class Object:
    name: str
    sql: str = field(repr=False)
    tbl_name: str

    def __post_init__(self) -> None:
        # This runtime type checking should arguably be in load_schema()
        if self.sql is None:
            cls = type(self).__name__.lower()
            raise TypeError(f"No SQL available for {cls} {self.name}")

    def __str__(self) -> str:
        return self.sql


class Index(Object):
    ...


class View(Object):
    ...


class Trigger(Object):
    ...


@dataclass
class Schema:
    tables: Dict[str, Table]
    indices: Dict[str, Index]
    views: Dict[str, View]
    triggers: Dict[str, Trigger]

    def difference(self, other: Schema) -> SchemaDiff:
        return schema_diff(self, other)


def _load_table(name: str, sql: str) -> Table:
    tree = create_table_parser().parse(sql)
    tables = cast(List[Table], TableTransformer().transform(tree).children)

    if len(tables) != 1:
        raise ValueError(f"Expected exactly 1 table definition, found {len(tables)}")

    table = tables[0]
    table.name = name
    table.sql = sql

    return table


def load_schema(conn: sqlite3.Connection) -> Schema:
    sql = "SELECT name, tbl_name, sql FROM sqlite_schema WHERE type = ? AND name NOT LIKE 'sqlite_%'"
    tables = conn.execute(sql, ("table",)).fetchall()
    indices = conn.execute(sql, ("index",)).fetchall()
    views = conn.execute(sql, ("view",)).fetchall()
    triggers = conn.execute(sql, ("trigger",)).fetchall()
    return Schema(
        tables={name: _load_table(name, sql) for name, _, sql in tables},
        indices={name: Index(name, sql, tbl_name) for name, tbl_name, sql in indices},
        views={name: View(name, sql, tbl_name) for name, tbl_name, sql in views},
        triggers={name: Trigger(name, sql, tbl_name) for name, tbl_name, sql in triggers},
    )
