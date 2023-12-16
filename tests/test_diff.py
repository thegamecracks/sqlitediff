import contextlib
import sqlite3

from sqlitediff import ModifiedTable, Schema, load_schema


def load_schema_from_sql(sql: str) -> Schema:
    with contextlib.closing(sqlite3.connect(":memory:")) as conn:
        conn.isolation_level = None
        conn.execute("PRAGMA foreign_keys = on")
        conn.executescript(sql)
        return load_schema(conn)


def test_shadowed_reference() -> None:
    old = load_schema_from_sql("""
        CREATE TABLE foo (x);
        CREATE INDEX bar ON foo (x);
        CREATE TRIGGER baz AFTER INSERT ON foo BEGIN DELETE FROM foo; END;

        CREATE VIEW baz (x) AS SELECT x FROM foo;
    """)
    new = load_schema_from_sql("""
        CREATE TABLE foo (x TEXT); -- Modified table
        CREATE INDEX bar ON foo (x);
        CREATE TRIGGER baz AFTER INSERT ON foo BEGIN DELETE FROM foo; END;

        CREATE VIEW baz (x) AS SELECT x FROM foo WHERE x > 'spam';
    """)
    # As of SQLite 3.44.2, views can have the same name as a trigger.
    # Despite view baz being present in the modified list, trigger baz
    # should still be included as a reference to the modified table.
    diff = new.difference(old)
    tables = [c for c in diff.modified if isinstance(c, ModifiedTable)]
    assert len(tables) == 1
    assert len(tables[0].references) == 2
