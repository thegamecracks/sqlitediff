import functools
import importlib.resources

import lark


@functools.lru_cache
def get_table_grammar() -> str:
    return importlib.resources.read_text(__package__, "table.lark")


def create_table_parser(*args, **kwargs) -> lark.Lark:
    grammar = get_table_grammar()
    return lark.Lark(grammar, *args, **kwargs)
