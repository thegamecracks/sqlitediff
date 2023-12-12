from pathlib import Path

import lark
import pytest

from sqlitediff.parser import TableTransformer, create_table_parser


@pytest.fixture(scope="session")
def table_parser() -> lark.Lark:
    return create_table_parser()


def test_one_column(table_parser: lark.Lark) -> None:
    tree = table_parser.parse("CREATE TABLE foo (x)")
    print(tree.pretty())

    tables = TableTransformer().transform(tree).children
    print(tables)


def test_two_columns(table_parser: lark.Lark) -> None:
    tree = table_parser.parse("CREATE TABLE foo (x, y)")
    print(tree.pretty())

    tables = TableTransformer().transform(tree).children
    print(tables)


def test_typed_columns(table_parser: lark.Lark) -> None:
    tree = table_parser.parse("CREATE TABLE foo (x INT, y INT)")
    print(tree.pretty())

    tables = TableTransformer().transform(tree).children
    print(tables)


def test_column_constraint(table_parser: lark.Lark) -> None:
    tree = table_parser.parse("CREATE TABLE foo (id INTEGER PRIMARY KEY)")
    print(tree.pretty())

    tables = TableTransformer().transform(tree).children
    print(tables)


def test_multi_column_constraint(table_parser: lark.Lark) -> None:
    tree = table_parser.parse("CREATE TABLE foo (id INTEGER PRIMARY KEY, bar TEXT NOT NULL)")
    print(tree.pretty())

    tables = TableTransformer().transform(tree).children
    print(tables)


def test_multi_constraint_column(table_parser: lark.Lark) -> None:
    tree = table_parser.parse("CREATE TABLE foo (bar TEXT UNIQUE NOT NULL)")
    print(tree.pretty())

    tables = TableTransformer().transform(tree).children
    print(tables)


def test_table_constraint(table_parser: lark.Lark) -> None:
    tree = table_parser.parse("CREATE TABLE foo (id, PRIMARY KEY (id))")
    print(tree.pretty())

    tables = TableTransformer().transform(tree).children
    print(tables)


def test_table_and_column_constraint(table_parser: lark.Lark) -> None:
    tree = table_parser.parse("CREATE TABLE foo (x INTEGER PRIMARY KEY, FOREIGN KEY (id) REFERENCES bar (x))")
    print(tree.pretty())

    tables = TableTransformer().transform(tree).children
    print(tables)


def test_table_option(table_parser: lark.Lark) -> None:
    tree = table_parser.parse("CREATE TABLE foo (x INTEGER) STRICT")
    print(tree.pretty())

    tables = TableTransformer().transform(tree).children
    print(tables)


def test_table_options(table_parser: lark.Lark) -> None:
    tree = table_parser.parse("CREATE TABLE foo (x TEXT PRIMARY KEY) STRICT, WITHOUT ROWID")
    print(tree.pretty())

    tables = TableTransformer().transform(tree).children
    print(tables)


def test_image_tags(table_parser: lark.Lark) -> None:
    path = Path(__file__).parent / "image_tags.sql"
    tree = table_parser.parse(path.read_text())
    print(tree.pretty())

    tables = TableTransformer().transform(tree).children
    print(tables)
