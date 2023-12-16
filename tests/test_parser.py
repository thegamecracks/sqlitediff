from pathlib import Path

import lark
import pytest

from sqlitediff.parser import TableTransformer, create_table_parser


@pytest.fixture(scope="session")
def table_parser() -> lark.Lark:
    return create_table_parser()


@pytest.mark.parametrize(
    "sql",
    [
        "CREATE TABLE foo (x)",
        "CREATE TABLE foo (x, y)",
        "CREATE TABLE foo (x INT, y INT)",
        "CREATE TABLE foo (id INTEGER PRIMARY KEY)",
        "CREATE TABLE foo (id INTEGER PRIMARY KEY, bar TEXT NOT NULL)",
        "CREATE TABLE foo (bar TEXT UNIQUE NOT NULL)",
        "CREATE TABLE foo (id, PRIMARY KEY (id))",
        "CREATE TABLE foo (x INTEGER PRIMARY KEY, FOREIGN KEY (id) REFERENCES bar (x))",
        "CREATE TABLE foo (x INTEGER) STRICT",
        "CREATE TABLE foo (x TEXT PRIMARY KEY) STRICT, WITHOUT ROWID",
        'CREATE TABLE "foo" (x)',
        'CREATE TABLE "foo ""bar""" (x)',
    ],
    ids=[
        "one-column",
        "two-columns",
        "typed-columns",
        "column-constraint",
        "multi-column-constraint",
        "multi-constraint-column",
        "table-constriant",
        "table-and-column-constraint",
        "table-option",
        "table-options",
        "quoted-table-name",
        "quotes-in-quoted-table-name",
    ],
)
def test_table_parser(table_parser: lark.Lark, sql: str) -> None:
    tree = table_parser.parse(sql)
    print(tree.pretty())

    tables = TableTransformer().transform(tree).children
    print(tables)


def test_image_tags(table_parser: lark.Lark) -> None:
    path = Path(__file__).parent / "image_tags.sql"
    tree = table_parser.parse(path.read_text())
    print(tree.pretty())

    tables = TableTransformer().transform(tree).children
    print(tables)
