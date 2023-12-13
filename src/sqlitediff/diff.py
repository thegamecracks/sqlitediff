from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Literal, Protocol, TypeVar

if TYPE_CHECKING:
    from .schema import Column, Schema, Table

T = TypeVar("T")


class Change(Protocol):
    def to_sql(self) -> str:
        raise NotImplementedError


@dataclass
class NewTable(Change):
    table: Table

    def to_sql(self) -> str:
        if self.table.sql is None:
            raise ValueError(f"No source SQL available for {self.table.name} table")
        return self.table.sql


@dataclass
class ModifiedTable(Change):
    old: Table
    new: Table

    def to_sql(self) -> str:
        if self.new.sql is None:
            raise ValueError(f"No source SQL available for {self.new.name} table")

        columns = ", ".join(c.name for c in self.old.columns.values())
        return (
            f"ALTER TABLE {self.old.name} RENAME TO sqlitediff_temp;\n"
            f"{self.new.sql};\n"
            f"INSERT INTO {self.new.name} ({columns}) SELECT * FROM sqlitediff_temp;\n"
            f"DROP TABLE sqlitediff_temp;"
        )


@dataclass
class DeletedTable(Change):
    table: Table

    def to_sql(self) -> str:
        return f"DELETE TABLE {self.table.name};"


@dataclass
class NewColumn(Change):
    table: Table
    column: Column

    def to_sql(self) -> str:
        return f"ALTER TABLE {self.table.name} ADD COLUMN {self.column.to_sql()};"


@dataclass
class ModifiedColumn(Change):
    table: Table
    old: Column
    new: Column

    def to_sql(self) -> str:
        raise TypeError(
            f"Column ({self.new.name}) for table {self.table.name} cannot be modified "
            f"in-place as SQLite does not support it."
        )


@dataclass
class DeletedColumn(Change):
    table: Table
    column: Column

    def to_sql(self) -> str:
        return f"ALTER TABLE {self.table.name} DROP COLUMN {self.column.name};"


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
    sql: str = field(repr=False)

    def to_sql(self) -> str:
        return f"DROP {self.type.upper()} {self.name};\n{self.sql};"


@dataclass
class DeletedObject(Change):
    type: ObjectType
    name: str

    def to_sql(self) -> str:
        return f"DROP {self.type.upper()} {self.name};"


@dataclass
class SchemaDiff:
    new: List[Change]
    modified: List[Change]
    deleted: List[Change]

    def extend(self, diff: SchemaDiff) -> None:
        self.new.extend(diff.new)
        self.modified.extend(diff.modified)
        self.deleted.extend(diff.deleted)

    def to_sql(self) -> str:
        grouped_changes = {
            "modified": self.modified,
            "deleted": self.deleted,
            "new": self.new
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


def _column_diff(
    table: Table,
    new: Dict[str, Column],
    old: Dict[str, Column],
) -> SchemaDiff:
    diff = SchemaDiff(new=[], modified=[], deleted=[])

    for name in new.keys() - old.keys():
        diff.new.append(NewColumn(table, new[name]))

    for name in new.keys() & old.keys():
        if new[name] != old[name]:
            diff.modified.append(ModifiedColumn(table, old[name], new[name]))

    for name in old.keys() - new.keys():
        diff.deleted.append(DeletedColumn(table, old[name]))

    return diff


def _table_diff(new: Dict[str, Table], old: Dict[str, Table]) -> SchemaDiff:
    diff = SchemaDiff(new=[], modified=[], deleted=[])

    for name in new.keys() - old.keys():
        diff.new.append(NewTable(new[name]))

    for name in new.keys() & old.keys():
        new_table = new[name]
        old_table = old[name]

        must_recreate_table = (
            new_table.constraints != old_table.constraints
            or new_table.options != old_table.options
        )

        if not must_recreate_table:
            column_diff = _column_diff(new_table, new_table.columns, old_table.columns)
            if len(column_diff.modified) > 0:
                must_recreate_table = True
            else:
                diff.extend(column_diff)

        if must_recreate_table:
            diff.modified.append(ModifiedTable(old_table, new_table))

    for name in old.keys() - new.keys():
        diff.deleted.append(DeletedTable(old[name]))

    return diff


def _object_diff(
    type: ObjectType,
    new: Dict[str, T],
    old: Dict[str, T],
) -> SchemaDiff:
    diff = SchemaDiff(new=[], modified=[], deleted=[])

    for name in new.keys() - old.keys():
        diff.new.append(NewObject(str(new[name])))

    for name in new.keys() & old.keys():
        if new[name] != old[name]:
            # FIXME: name must be escaped
            change = ModifiedObject(type=type, name=name, sql=str(new[name]))
            diff.modified.append(change)

    for name in old.keys() - new.keys():
        # FIXME: name must be escaped
        diff.deleted.append(DeletedObject(type=type, name=name))

    return diff


def schema_diff(new: Schema, old: Schema) -> SchemaDiff:
    diff = SchemaDiff(new=[], modified=[], deleted=[])

    diff.extend(_table_diff(new.tables, old.tables))
    diff.extend(_object_diff("index", new.indices, old.indices))
    diff.extend(_object_diff("view", new.views, old.views))
    diff.extend(_object_diff("trigger", new.triggers, old.triggers))

    return diff
