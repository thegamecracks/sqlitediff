import contextlib
import sqlite3
from pathlib import Path

import pytest

from sqlitediff.schema import load_schema


@pytest.mark.parametrize(
    "path",
    [
        Path("examples/user_group_1.sql"),
        Path("examples/user_group_2.sql"),
    ],
    ids=[
        "user-group-1",
        "user-group-2",
    ],
)
def test_load_schema(path: Path):
    with contextlib.closing(sqlite3.connect(":memory:")) as conn:
        conn.executescript(path.read_text())
        schema = load_schema(conn)

    print(schema)


@pytest.mark.parametrize(
    "old_path,new_path",
    [
        (Path("examples/user_group_1.sql"), Path("examples/user_group_2.sql")),
    ],
    ids=[
        "user-group-1-2",
    ],
)
def test_schema_diff(old_path: Path, new_path: Path):
    with contextlib.closing(sqlite3.connect(":memory:")) as conn:
        conn.executescript(old_path.read_text())
        old_schema = load_schema(conn)

    with contextlib.closing(sqlite3.connect(":memory:")) as conn:
        conn.executescript(new_path.read_text())
        new_schema = load_schema(conn)

    diff = new_schema.difference(old_schema)
    print(diff.to_sql())
