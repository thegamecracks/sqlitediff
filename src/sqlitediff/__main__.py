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

Some checks will be performed on the resulting diff to warn about
potential issues with the migration script, such as table/column
renames that sqlitediff cannot detect, and DROP COLUMN constraint
violations.
"""
import argparse
import contextlib
import logging
import sqlite3
import textwrap
from pathlib import Path
from typing import Iterable, Iterator, List, Type, TypeVar, Union

import sqlitediff
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

log = logging.getLogger(__name__)

T = TypeVar("T")


def filter_type(cls: Type[T], it: Iterable[object]) -> Iterator[T]:
    for obj in it:
        if isinstance(obj, cls):
            yield obj


def contains_type(cls: Type[object], it: Iterable[object]) -> bool:
    for _ in filter_type(cls, it):
        return True
    return False


def has_new_and_deleted_tables(diff: SchemaDiff) -> bool:
    if not contains_type(NewTable, diff.new):
        return False
    if not contains_type(DeletedTable, diff.deleted):
        return False
    return True


def has_new_and_deleted_columns(diff: SchemaDiff) -> bool:
    if not contains_type(NewColumn, diff.new):
        return False
    if not contains_type(DeletedColumn, diff.deleted):
        return False
    return True


def column_will_be_dropped(diff: SchemaDiff) -> bool:
    if contains_type(ModifiedColumn, diff.modified):
        return True
    if contains_type(DeletedColumn, diff.deleted):
        return True
    return False


def valid_column_default(column: Column) -> bool:
    nullable = True
    null_default = True
    for c in column.constraints:
        c = c.upper()
        nullable = nullable and "NOT NULL" not in c
        null_default = null_default and ("DEFAULT" not in c or "DEFAULT NULL" in c)
    return nullable or not null_default


def _log_invalid_default(table: str, column: str) -> None:
    log.info("%s.%s default may be invalid", table, column, stacklevel=2)


def all_column_changes_have_valid_defaults(diff: SchemaDiff) -> bool:
    ret = True
    for c in filter_type(NewColumn, diff.new):
        if not valid_column_default(c.column):
            _log_invalid_default(c.table.raw_name, c.column.raw_name)
            ret = False
    for c in filter_type(ModifiedColumn, diff.modified):
        if not valid_column_default(c.new):
            _log_invalid_default(c.table.raw_name, c.new.raw_name)
            ret = False
    return ret


def sql_diff_checklist(diff: SchemaDiff) -> str:
    # Checklist should be written to suit the phrase, "Please make sure that..."
    checklist: List[str] = []

    if has_new_and_deleted_tables(diff) or has_new_and_deleted_columns(diff):
        checklist.append(
            "Any new tables or columns were not intended to be renames\n"
            "of existing tables/columns. If this appears to be the case,\n"
            "please replace the corresponding queries with an ALTER TABLE\n"
            "statement to prevent data loss."
        )

    if column_will_be_dropped(diff):
        checklist.append(
            "Any DROP COLUMN statements are not referenced by another\n"
            "view, check, foreign key, trigger, or index, including\n"
            "PRIMARY KEY and UNIQUE constraints. If this is the case,\n"
            "those references must be dropped before the column.\n"
            "https://sqlite.org/lang_altertable.html#alter_table_drop_column"
        )

    if not all_column_changes_have_valid_defaults(diff):
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


class CommentFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        return sql_comment(message)


def configure_logging(verbose: int) -> None:
    if verbose == 0:
        return
    elif verbose == 1:
        fmt = "%(levelname)s: %(message)s"
        level = logging.INFO
    else:
        fmt = "%(levelname)s: %(message)-50s (%(name)s#L%(lineno)d)"
        level = logging.DEBUG

    formatter = CommentFormatter(fmt=fmt)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    log = logging.getLogger()
    log.addHandler(handler)
    log.setLevel(level)


def main():
    parser = argparse.ArgumentParser(
        prog=__package__,
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase logging verbosity",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"{__package__} {sqlitediff.__version__}",
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

    configure_logging(args.verbose)

    with contextlib.closing(args.conn_old) as conn:
        old_schema = load_schema(conn)

    with contextlib.closing(args.conn_new) as conn:
        new_schema = load_schema(conn)

    diff = schema_diff(new_schema, old_schema)

    if diff.total_changes == 0:
        return print("-- No differences found")

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
        f"-- Please verify foreign keys before committing!\n"
        f"-- The following pragma should return 0 rows:\n"
        f"PRAGMA foreign_key_check;\n"
        f"\n"
        f"COMMIT;\n",
        end="",
    )


if __name__ == "__main__":
    main()
