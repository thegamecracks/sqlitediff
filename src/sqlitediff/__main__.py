"""
Compares the schemas of two SQLite databases and generates
a simplified SQL script for aiding migrations.

This tool is intended to help with schema migrations when
a migration script wasn't hand-crafted beforehand, and should
not be used for automated migrations as it cannot determine
the best way to migrate a schema without data loss.

The `from` or `to` arguments can be passed an .sql file instead of
an SQLite database, in which case the contents will be executed in
an in-memory database before being compared.
"""
import argparse
import contextlib
import sqlite3
import textwrap
from pathlib import Path
from typing import List, Union

from .diff import (
    DeletedColumn,
    DeletedTable,
    ModifiedColumn,
    NewColumn,
    NewTable,
    SchemaDiff,
    schema_diff,
)
from .escapes import sql_comment
from .schema import Column, load_schema


def valid_column_default(column: Column) -> bool:
    nullable = True
    null_default = False
    for c in column.constraints:
        c = c.upper()
        nullable = nullable and "NOT NULL" in c
        null_default = null_default or "DEFAULT" in c and not "DEFAULT NULL" in c
    return nullable or not null_default


def sql_diff_checklist(diff: SchemaDiff) -> str:
    checklist: List[str] = []

    if any(isinstance(c, (NewTable, NewColumn)) for c in diff.new) and any(
        isinstance(c, (DeletedTable, DeletedColumn)) for c in diff.deleted
    ):
        checklist.append(
            "Any new tables or columns were not intended to be renames\n"
            "of existing tables/columns. If this appears to be the case,\n"
            "please replace the corresponding queries with an ALTER TABLE\n"
            "statement to prevent data loss."
        )

    if any(
        isinstance(c, NewColumn) and not valid_column_default(c.column)
        for c in diff.new
    ) or any(
        isinstance(c, ModifiedColumn) and not valid_column_default(c.new)
        for c in diff.modified
    ):
        checklist.append(
            "All ADD COLUMN statements have a valid default value.\n"
            "If a NOT NULL constraint is present, make sure it has\n"
            "a DEFAULT constraint."
        )

    indent = 5
    i_end = indent - 1
    i_start = i_end - 3
    for i, message in enumerate(checklist):
        message = textwrap.indent(message, " " * indent)
        message = message[:i_start] + f"{i + 1:>2d}." + message[i_end:]
        checklist[i] = message

    return sql_comment("\n".join(checklist))


def connect_by_path(path: Union[str, Path]) -> sqlite3.Connection:
    path = Path(path)

    if path.suffix.endswith(".sql"):
        conn = sqlite3.connect(":memory:")
        conn.executescript(path.read_text("utf-8"))
    else:
        conn = sqlite3.connect(path)

    return conn


def main():
    parser = argparse.ArgumentParser(
        prog=__package__,
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        metavar="from",
        dest="conn_old",
        help="The database with the old schema to be updated",
        type=connect_by_path,
    )
    parser.add_argument(
        metavar="to",
        dest="conn_new",
        help="The database with the newer schema to update to",
        type=connect_by_path,
    )

    args = parser.parse_args()

    with contextlib.closing(args.conn_old) as conn:
        old_schema = load_schema(conn)

    with contextlib.closing(args.conn_new) as conn:
        new_schema = load_schema(conn)
        foreign_keys = conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    diff = schema_diff(new_schema, old_schema)
    sql = diff.to_sql()

    checklist = sql_diff_checklist(diff)
    if checklist:
        print("-- Before running the following script, please make sure that:")
        print(checklist)

    print(
        f"PRAGMA foreign_keys = off;\n"
        f"BEGIN TRANSACTION;\n"
        f"\n"
        f"{sql}\n"
        f"\n"
        f"COMMIT;\n"
        f"PRAGMA foreign_keys = {'on' if foreign_keys else 'off'}; "
        f"-- As initially configured by database\n",
        end="",
    )


if __name__ == "__main__":
    main()
