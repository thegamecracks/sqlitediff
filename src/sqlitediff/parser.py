import functools
import importlib.resources

import lark


@functools.lru_cache
def get_table_grammar() -> str:
    return importlib.resources.read_text(__package__, "table.lark")


def create_table_parser(*args, **kwargs) -> lark.Lark:
    grammar = get_table_grammar()
    return lark.Lark(grammar, *args, **kwargs)


class TableTransformer(lark.Transformer):
    def name(self, children):
        return str(children[0])

    def type(self, children):
        return str(children[0])

    def unknown_token(self, children):
        return " ".join(children)

    def column_constraint(self, children):
        return " ".join(children)

    def column(self, children):
        from .schema import Column

        if len(children) < 2:
            children.append(None)

        return Column(raw_name=children[0], type=children[1], constraints=set(children[2:]))

    def columns(self, children):
        return {column.raw_name: column for column in children}

    def table_constraint(self, children):
        return " ".join(children)

    def table_constraints(self, children):
        return set(children)

    def table_option(self, children):
        return " ".join(children)

    def table_options(self, children):
        return set(children)

    def create_table(self, children):
        from .schema import Table

        if len(children) < 3:
            children.append(set())
        if len(children) < 4:
            children.append(set())

        return Table(
            name="missing true name",  # this will be filled in by load_schema()
            raw_name=children[0],
            columns=children[1],
            constraints=children[2],
            options=children[3],
        )

    def statement(self, children):
        return children[0]
