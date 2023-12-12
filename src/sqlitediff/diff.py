from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Literal, Protocol, Tuple, TypeVar

if TYPE_CHECKING:
    from .schema import Column, Schema, Table

T = TypeVar("T")


class Change(Protocol):
    def to_sql(self) -> str:
        raise NotImplementedError


@dataclass
class NewColumn(Change):
    table: Table
    column: Column

    def to_sql(self) -> str:
        return f"ALTER TABLE {self.table.name} ADD COLUMN {self.column.to_sql()};"


@dataclass
class DeletedColumn(Change):
    table: Table
    column: Column

    def to_sql(self) -> str:
        return f"ALTER TABLE {self.table.name} DROP COLUMN {self.column.name};"


ObjectType = Literal["index", "view", "trigger"]


@dataclass
class NewObject(Change):
    sql: str

    def to_sql(self) -> str:
        return self.sql


@dataclass
class ModifiedObject(Change):
    type: ObjectType
    name: str
    sql: str

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
        statements: List[str] = []
        for change in itertools.chain(self.modified, self.deleted, self.new):
            statements.append(change.to_sql())
        return "\n".join(statements)


def _object_diff(
    type: ObjectType,
    new: Dict[str, T],
    old: Dict[str, T],
) -> SchemaDiff:
    _new: List[Change] = []
    for name in new.keys() - old.keys():
        _new.append(NewObject(str(new[name])))

    _modified: List[Change] = []
    for name in new.keys() & old.keys():
        if new[name] != old[name]:
            # FIXME: name must be escaped
            change = ModifiedObject(type=type, name=name, sql=str(new[name]))
            _modified.append(change)

    _deleted: List[Change] = []
    for name in old.keys() - new.keys():
        # FIXME: name must be escaped
        _deleted.append(DeletedObject(type=type, name=name))

    return SchemaDiff(
        new=_new,
        modified=_modified,
        deleted=_deleted,
    )


def schema_diff(new: Schema, old: Schema) -> SchemaDiff:
    diff = SchemaDiff(new=[], modified=[], deleted=[])

    # TODO: table diffs

    diff.extend(_object_diff("index", new.indices, old.indices))
    diff.extend(_object_diff("view", new.views, old.views))
    diff.extend(_object_diff("trigger", new.triggers, old.triggers))

    return diff
