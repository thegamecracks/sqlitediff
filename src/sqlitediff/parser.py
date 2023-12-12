import importlib.resources

import lark


def create_table_parser() -> lark.Lark:
    grammar = importlib.resources.read_text(__package__, "table.lark")
    return lark.Lark(grammar)
