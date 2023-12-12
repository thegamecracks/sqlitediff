import contextlib
import sqlite3
from pathlib import Path

from sqlitediff.schema import load_schema


def test_load_user_group_1():
    path = Path(__file__).parent / "user_group_1.sql"
    with contextlib.closing(sqlite3.connect(":memory:")) as conn:
        conn.executescript(path.read_text())
        schema = load_schema(conn)

    print(schema)


def test_load_user_group_2():
    path = Path(__file__).parent / "user_group_1.sql"
    with contextlib.closing(sqlite3.connect(":memory:")) as conn:
        conn.executescript(path.read_text())
        schema = load_schema(conn)

    print(schema)


def test_user_group_1_diff_2():
    path_1 = Path(__file__).parent / "user_group_1.sql"
    path_2 = Path(__file__).parent / "user_group_2.sql"

    with contextlib.closing(sqlite3.connect(":memory:")) as conn:
        conn.executescript(path_1.read_text())
        schema_1 = load_schema(conn)

    with contextlib.closing(sqlite3.connect(":memory:")) as conn:
        conn.executescript(path_2.read_text())
        schema_2 = load_schema(conn)

    diff = schema_2.difference(schema_1)
    print(diff.to_sql())
