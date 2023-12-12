from dataclasses import dataclass, field
from typing import Dict, NewType, Optional, Set

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
    indices: Set[Index]
    views: Set[View]
    triggers: Set[Trigger]
