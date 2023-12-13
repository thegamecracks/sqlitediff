from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Literal, Protocol, Sequence, TypeVar

from .escapes import sql_comment

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
    associations: List[RestoredObject] = field(default_factory=list)

    def to_sql(self) -> str:
        if self.old.sql is None:
            raise ValueError(f"No source SQL available for {self.old.name} table")
        if self.new.sql is None:
            raise ValueError(f"No source SQL available for {self.new.name} table")

        columns = ", ".join(c.name for c in self.old.columns.values())
        sql = [
            f"-- Previous table schema for {self.old.name}:",
            f"{sql_comment(self.old.sql + ';')}",
            f"ALTER TABLE {self.old.name} RENAME TO sqlitediff_temp;",
            f"{self.new.sql};",
            f"INSERT INTO {self.new.name} ({columns}) SELECT * FROM sqlitediff_temp;",
            f"DROP TABLE sqlitediff_temp;",
        ]

        if len(self.associations) > 0:
            sql.append("")
            sql.append(f"-- Restoring associations for {self.new.name}:")
            sql.extend(a.sql + ";" for a in self.associations)

        return "\n".join(sql)


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
            f"Column {self.new.name} for table {self.table.name} cannot be modified "
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
    old: str = field(repr=False)
    new: str = field(repr=False)

    def to_sql(self) -> str:
        # FIXME: name field is not escaped
        return (
            f"-- Previous {self.type} schema for {self.name}:\n"
            f"{sql_comment(self.old + ';')}\n"
            f"DROP {self.type.upper()} IF EXISTS {self.name};\n"
            f"{self.new};"
        )


@dataclass
class DeletedObject(Change):
    type: ObjectType
    name: str

    def to_sql(self) -> str:
        # FIXME: name field is not escaped
        return f"DROP {self.type.upper()} IF EXISTS {self.name};"


@dataclass
class RestoredObject(Change):
    sql: str

    def to_sql(self) -> str:
        return self.sql + ";"


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
            change = ModifiedObject(
                type=type,
                name=name,
                old=str(old[name]),
                new=str(new[name]),
            )
            diff.modified.append(change)

    for name in old.keys() - new.keys():
        diff.deleted.append(DeletedObject(type=type, name=name))

    return diff


class Association(Protocol):
    name: str
    tbl_name: str


def _is_association_modified(o: Association, diff: SchemaDiff) -> bool:
    for c in diff.modified:
        if isinstance(c, ModifiedObject) and c.name == o.name:
            return True
    for c in diff.deleted:
        if isinstance(c, DeletedObject) and c.name == o.name:
            return True
    return False


def _add_table_associations(diff: SchemaDiff, objects: Sequence[Association]) -> None:
    modified = [c for c in diff.modified if isinstance(c, ModifiedTable)]

    # O(n*m*k) tradeoff for code simplicity
    associations: List[List[Association]] = []
    for c in modified:
        arr: List[Association] = []
        for o in objects:
            if o.tbl_name != c.new.name:
                continue
            if _is_association_modified(o, diff):
                continue
            arr.append(o)
        associations.append(arr)

    for table, objects in zip(modified, associations):
        for o in objects:
            table.associations.append(RestoredObject(str(o)))


def schema_diff(new: Schema, old: Schema) -> SchemaDiff:
    diff = SchemaDiff(new=[], modified=[], deleted=[])

    diff.extend(_table_diff(new.tables, old.tables))
    diff.extend(_object_diff("index", new.indices, old.indices))
    diff.extend(_object_diff("view", new.views, old.views))
    diff.extend(_object_diff("trigger", new.triggers, old.triggers))

    _add_table_associations(diff, tuple(old.indices.values()))
    _add_table_associations(diff, tuple(old.views.values()))
    _add_table_associations(diff, tuple(old.triggers.values()))

    return diff
