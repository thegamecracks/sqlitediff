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
