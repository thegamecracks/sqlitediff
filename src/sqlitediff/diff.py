from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    List,
    Literal,
    Optional,
    Protocol,
    Sequence,
    TypeVar,
)

from .escapes import sql_comment, sql_identifier

if TYPE_CHECKING:
    from .schema import Column, Schema, Table

log = logging.getLogger(__name__)

K = TypeVar("K")
T = TypeVar("T")
V = TypeVar("V")


class Change(Protocol):
    def to_sql(self) -> str:
        raise NotImplementedError


@dataclass
class NewTable(Change):
    table: Table

    def to_sql(self) -> str:
        if self.table.sql is None:
            raise ValueError(f"No source SQL available for {self.table.raw_name} table")
        return self.table.sql


@dataclass
class ModifiedTable(Change):
    old: Table
    new: Table
    references: List[ReferencedObject] = field(default_factory=list)

    def to_sql(self) -> str:
        if self.old.sql is None:
            raise ValueError(f"No source SQL available for {self.old.raw_name} table")
        if self.new.sql is None:
            raise ValueError(f"No source SQL available for {self.new.raw_name} table")

        common_columns = self.new.columns.keys() & self.old.columns.keys()
        columns = ", ".join(self.old.columns[name].raw_name for name in common_columns)

        new_sql_temp = self.new.sql.replace(
            f"CREATE TABLE {self.new.raw_name}",
            "CREATE TABLE sqlitediff_temp",
            1
        )
        if new_sql_temp == self.new.sql:
            raise ValueError(f"Table {self.new.name} SQL does not match name")

        sql = [
            f"-- Previous table schema for {self.old.raw_name}:",
            f"{sql_comment(self.old.sql + ';')}",
            f"{new_sql_temp};",
            f"INSERT INTO sqlitediff_temp ({columns}) SELECT {columns} FROM {self.old.raw_name};",
            f"DROP TABLE {self.old.raw_name};",
            f"ALTER TABLE sqlitediff_temp RENAME TO {self.new.raw_name};",
        ]

        if len(self.references) > 0:
            sql.append("")
            sql.append(f"-- Restoring references to {self.new.raw_name}:")
            sql.extend(a.to_sql() for a in self.references)

        return "\n".join(sql)


@dataclass
class DeletedTable(Change):
    table: Table

    def to_sql(self) -> str:
        return f"DELETE TABLE {self.table.raw_name};"


@dataclass
class NewColumn(Change):
    table: Table
    column: Column

    def to_sql(self) -> str:
        return f"ALTER TABLE {self.table.raw_name} ADD COLUMN {self.column.to_sql()};"


@dataclass
class ModifiedColumn(Change):
    table: Table
    old: Column
    new: Column

    def to_sql(self) -> str:
        raise TypeError(
            f"Column {self.new.raw_name} for table {self.table.raw_name} cannot be modified "
            f"in-place as SQLite does not support it."
        )


@dataclass
class DeletedColumn(Change):
    table: Table
    column: Column

    def to_sql(self) -> str:
        return f"ALTER TABLE {self.table.raw_name} DROP COLUMN {self.column.raw_name};"


ObjectType = Literal["index", "view", "trigger"]


@dataclass
class NewObject(Change):
    sql: str = field(repr=False)

    def to_sql(self) -> str:
        return self.sql + ";"


@dataclass
class ModifiedObject(Change):
    type: ObjectType
    name: str
    old: str = field(repr=False)
    new: str = field(repr=False)

    def to_sql(self) -> str:
        name = sql_identifier(self.name, as_needed=True)
        return (
            f"-- Previous {self.type} schema for {self.name}:\n"
            f"{sql_comment(self.old + ';')}\n"
            f"DROP {self.type.upper()} IF EXISTS {name};\n"
            f"{self.new};"
        )


@dataclass
class DeletedObject(Change):
    type: ObjectType
    name: str

    def to_sql(self) -> str:
        name = sql_identifier(self.name, as_needed=True)
        return f"DROP {self.type.upper()} IF EXISTS {name};"


@dataclass
class ReferencedObject(Change):
    sql: str

    def to_sql(self) -> str:
        return self.sql + ";"


@dataclass
class SchemaDiff:
    new: List[Change]
    modified: List[Change]
    deleted: List[Change]

    @property
    def total_changes(self) -> int:
        return len(self.new) + len(self.modified) + len(self.deleted)

    def extend(self, diff: SchemaDiff) -> None:
        self.new.extend(diff.new)
        self.modified.extend(diff.modified)
        self.deleted.extend(diff.deleted)

    def to_sql(self) -> str:
        grouped_changes = {
            "modified": self.modified,
            "deleted": self.deleted,
            "new": self.new,
        }

        grouped_statements: List[str] = []
        for group, changes in grouped_changes.items():
            if len(changes) == 0:
                continue

            statements = [f"-- {group.title()} Objects --"]
            for change in changes:
                statements.append(change.to_sql())
            grouped_statements.append("\n\n".join(statements))

        return "\n\n".join(grouped_statements)


def _dict_diff(new: Dict[K, V], old: Iterable[Any]) -> Dict[K, V]:
    # Unlike new.keys() - old.keys(), this retains order
    new = new.copy()
    for key in old:
        try:
            new.pop(key)
        except KeyError:
            pass
    return new


def _column_diff(
    table: Table,
    new: Dict[str, Column],
    old: Dict[str, Column],
) -> SchemaDiff:
    diff = SchemaDiff(new=[], modified=[], deleted=[])

    for name in _dict_diff(new, old):
        diff.new.append(NewColumn(table, new[name]))

    for name in new.keys() & old.keys():
        if new[name] != old[name]:
            diff.modified.append(ModifiedColumn(table, old[name], new[name]))

    for name in _dict_diff(old, new):
        diff.deleted.append(DeletedColumn(table, old[name]))

    return diff


def _diff_matches_column_order(
    diff: SchemaDiff,
    new: Dict[str, Column],
    old: Dict[str, Column],
) -> bool:
    altered = old.copy()

    for c in diff.deleted:
        if isinstance(c, DeletedColumn):
            del altered[c.column.raw_name]

    for c in diff.new:
        if isinstance(c, NewColumn):
            altered[c.column.raw_name] = c.column

    return tuple(altered) == tuple(new)


def _table_diff(new: Dict[str, Table], old: Dict[str, Table]) -> SchemaDiff:
    diff = SchemaDiff(new=[], modified=[], deleted=[])

    for name in new.keys() - old.keys():
        log.info("New table: %s", name)
        diff.new.append(NewTable(new[name]))

    for name in new.keys() & old.keys():
        new_table = new[name]
        old_table = old[name]
        must_recreate_table = False

        if new_table.constraints != old_table.constraints:
            log.info("Modified table constraints: %s", name)
            must_recreate_table = True

        if new_table.options != old_table.options:
            log.info("Modified table options: %s", name)
            must_recreate_table = True

        column_diff = _column_diff(new_table, new_table.columns, old_table.columns)
        if len(column_diff.modified) > 0:
            log.info("Modified table columns: %s", name)
            must_recreate_table = True

        new_columns = new_table.columns
        old_columns = old_table.columns
        if not _diff_matches_column_order(column_diff, new_columns, old_columns):
            log.info("Re-ordered table columns: %s", name)
            must_recreate_table = True

        if must_recreate_table:
            diff.modified.append(ModifiedTable(old_table, new_table))
        else:
            diff.extend(column_diff)

    for name in old.keys() - new.keys():
        log.info("Deleted table: %s", name)
        diff.deleted.append(DeletedTable(old[name]))

    return diff


def _object_diff(
    type: ObjectType,
    new: Dict[str, T],
    old: Dict[str, T],
) -> SchemaDiff:
    diff = SchemaDiff(new=[], modified=[], deleted=[])

    for name in new.keys() - old.keys():
        log.info("New %s: %s", type, name)
        diff.new.append(NewObject(str(new[name])))

    for name in new.keys() & old.keys():
        if new[name] != old[name]:
            log.info("Modified %s: %s", type, name)
            change = ModifiedObject(
                type=type,
                name=name,
                old=str(old[name]),
                new=str(new[name]),
            )
            diff.modified.append(change)

    for name in old.keys() - new.keys():
        log.info("Deleted %s: %s", type, name)
        diff.deleted.append(DeletedObject(type=type, name=name))

    return diff


class Reference(Protocol):
    name: str
    tbl_name: str


def _is_reference_modified(o: Reference, diff: SchemaDiff) -> bool:
    for c in diff.modified:
        if isinstance(c, ModifiedObject) and c.name == o.name:
            return True
    for c in diff.deleted:
        if isinstance(c, DeletedObject) and c.name == o.name:
            return True
    return False


def _add_table_references(diff: SchemaDiff, objects: Sequence[Reference]) -> None:
    modified = [c for c in diff.modified if isinstance(c, ModifiedTable)]

    # O(n*m*k) tradeoff for code simplicity
    references: List[List[Reference]] = []
    for c in modified:
        arr: List[Reference] = []
        for o in objects:
            if o.tbl_name != c.new.name:
                continue
            if _is_reference_modified(o, diff):
                continue
            arr.append(o)
        references.append(arr)

    for table, objects in zip(modified, references):
        for o in objects:
            log.info("%s to restore: %s", type(o).__name__, o.name)
            table.references.append(ReferencedObject(str(o)))


def schema_diff(new: Schema, old: Schema) -> SchemaDiff:
    diff = SchemaDiff(new=[], modified=[], deleted=[])

    diff.extend(_table_diff(new.tables, old.tables))
    diff.extend(_object_diff("index", new.indices, old.indices))
    diff.extend(_object_diff("view", new.views, old.views))
    diff.extend(_object_diff("trigger", new.triggers, old.triggers))

    _add_table_references(diff, tuple(old.indices.values()))
    _add_table_references(diff, tuple(old.views.values()))
    _add_table_references(diff, tuple(old.triggers.values()))

    return diff
