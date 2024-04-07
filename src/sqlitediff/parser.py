from __future__ import annotations

import functools
import importlib.resources
from typing import TYPE_CHECKING, Any, Dict, List, Set

import lark

if TYPE_CHECKING:
    from .schema import Column, Table


@functools.lru_cache
def get_table_grammar() -> str:
    assert __package__ is not None
    return importlib.resources.read_text(__package__, "table.lark")


def create_table_parser(*args, **kwargs) -> lark.Lark:
    grammar = get_table_grammar()
    return lark.Lark(grammar, *args, **kwargs)


class TableTransformer(lark.Transformer):
    def name(self, children: List[lark.Token]) -> str:
        return str(children[0])

    def type(self, children: List[lark.Token]) -> str:
        return str(children[0])

    def unknown_token(self, children: List[lark.Token]) -> str:
        return " ".join(children)

    def column_constraint(self, children: List[lark.Token]) -> str:
        return " ".join(children)

    def column(self, children: List[str]) -> Column:
        from .schema import Column, ColumnConstraint

        type = children[1] if len(children) > 1 else None
        constraints = set(ColumnConstraint(c) for c in children[2:])
        return Column(raw_name=children[0], type=type, constraints=constraints)

    def columns(self, children: List[Column]) -> Dict[str, Column]:
        return {column.raw_name: column for column in children}

    def table_constraint(self, children: List[lark.Token]) -> str:
        from .schema import TableConstraint

        return TableConstraint(" ".join(children))

    def table_constraints(self, children: List[str]) -> Set[str]:
        return set(children)

    def table_option(self, children: List[lark.Token]) -> str:
        from .schema import TableOption

        return TableOption(" ".join(children))

    def table_options(self, children: List[str]) -> Set[str]:
        return set(children)

    def create_table(self, children: List[Any]) -> Table:
        from .schema import Table

        constraints = children[2] if len(children) > 2 else set()
        options = children[3] if len(children) > 3 else set()

        return Table(
            name="missing true name",  # this will be filled in by load_schema()
            raw_name=children[0],
            columns=children[1],
            constraints=constraints,
            options=options,
        )

    def statement(self, children: List[Table]) -> Table:
        return children[0]
