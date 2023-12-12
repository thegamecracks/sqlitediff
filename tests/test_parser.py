import lark
import pytest

from sqlitediff.parser import create_table_parser


@pytest.fixture(scope="session")
def table_parser() -> lark.Lark:
    return create_table_parser()


def test_one_column(table_parser: lark.Lark) -> None:
    tree = table_parser.parse("CREATE TABLE foo (x)")
    print(tree.pretty())


def test_two_columns(table_parser: lark.Lark) -> None:
    tree = table_parser.parse("CREATE TABLE foo (x, y)")
    print(tree.pretty())


def test_typed_columns(table_parser: lark.Lark) -> None:
    tree = table_parser.parse("CREATE TABLE foo (x INT, y INT)")
    print(tree.pretty())


def test_column_constraint(table_parser: lark.Lark) -> None:
    tree = table_parser.parse("CREATE TABLE foo (id INTEGER PRIMARY KEY)")
    print(tree.pretty())


def test_multi_column_constraint(table_parser: lark.Lark) -> None:
    tree = table_parser.parse("CREATE TABLE foo (id INTEGER PRIMARY KEY, bar TEXT NOT NULL)")
    print(tree.pretty())


def test_multi_constraint_column(table_parser: lark.Lark) -> None:
    tree = table_parser.parse("CREATE TABLE foo (bar TEXT UNIQUE NOT NULL)")
    print(tree.pretty())


def test_table_constraint(table_parser: lark.Lark) -> None:
    tree = table_parser.parse("CREATE TABLE foo (id, PRIMARY KEY (id))")
    print(tree.pretty())


def test_table_and_column_constraint(table_parser: lark.Lark) -> None:
    tree = table_parser.parse("CREATE TABLE foo (x INTEGER PRIMARY KEY, FOREIGN KEY (id) REFERENCES bar (x))")
    print(tree.pretty())


def test_table_option(table_parser: lark.Lark) -> None:
    tree = table_parser.parse("CREATE TABLE foo (x INTEGER) STRICT")
    print(tree.pretty())


def test_table_options(table_parser: lark.Lark) -> None:
    tree = table_parser.parse("CREATE TABLE foo (x TEXT PRIMARY KEY) STRICT, WITHOUT ROWID")
    print(tree.pretty())
