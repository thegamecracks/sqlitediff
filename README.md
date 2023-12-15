# sqlitediff

[![](https://img.shields.io/github/actions/workflow/status/thegamecracks/sqlitediff/pyright-lint.yml?style=flat-square&label=pyright)](https://microsoft.github.io/pyright/#/)
[![](https://img.shields.io/github/actions/workflow/status/thegamecracks/sqlitediff/python-test.yml?style=flat-square&logo=pytest&label=tests)](https://docs.pytest.org/en/stable/)

A command-line program for generating SQLite schema diffs.

> [!NOTE]
>
> This project is not associated with [5f0ne](https://github.com/5f0ne)'s
> PyPI package, [sqlitediff](https://pypi.org/project/sqlitediff/),
> which caters towards analysis of data changes in an SQLite database.

```sql
$ sqlitediff examples/user_group_1.sql examples/user_group_2.sql
PRAGMA foreign_keys = off;
BEGIN TRANSACTION;

-- Modified Objects --

-- Previous table schema for user:
-- CREATE TABLE user (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE sqlitediff_temp (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
INSERT INTO sqlitediff_temp (id, name) SELECT id, name FROM user;
DROP TABLE user;
ALTER TABLE sqlitediff_temp RENAME TO user;

-- Restoring references to user:
CREATE INDEX ix_user_name ON user (name);

-- Previous view schema for user_group_kawaii:
-- CREATE VIEW user_group_kawaii (id) AS
--     SELECT user_id FROM user_group WHERE group_id = 1;
DROP VIEW IF EXISTS user_group_kawaii;
CREATE VIEW user_group_kawaii (id) AS
    SELECT user_id FROM user_group WHERE group_id = 2;

-- Previous trigger schema for add_user_to_kawaii_group:
-- CREATE TRIGGER add_user_to_kawaii_group
--     INSERT ON user
--     BEGIN
--         INSERT INTO user_group (user_id, group_id) VALUES (new.id, 1);
--     END;
DROP TRIGGER IF EXISTS add_user_to_kawaii_group;
CREATE TRIGGER add_user_to_kawaii_group
    INSERT ON user
    BEGIN
        INSERT INTO user_group (user_id, group_id) VALUES (new.id, 2);
    END;

-- New Objects --

ALTER TABLE "group" ADD COLUMN description TEXT NOT NULL DEFAULT '';

CREATE INDEX ix_group_user ON user_group (group_id, user_id);

CREATE VIEW user_group_all (id) AS
    SELECT user_id FROM user_group WHERE group_id = 1;

CREATE TRIGGER add_user_to_all_group
    INSERT ON user
    BEGIN
        INSERT INTO user_group (user_id, group_id) VALUES (new.id, 1);
    END;

-- Please verify foreign keys before committing!
-- The following pragma should return 0 rows:
PRAGMA foreign_key_check;

COMMIT;
```

sqlitediff uses the [`sqlite_schema`] table to read your database structure
and compare differences between tables, indices, views, and triggers.
It can parse DDL for tables to determine new, modified, or deleted columns
and tries to produce [ALTER TABLE] statements where supported by SQLite.
Additionally, recommendations will be provided if sqlitediff detects
potential issues with the output script such as table/column renames.

> [!WARNING]
>
> Do not run sqlitediff's output on a production database un-modified
> without first verifying that the script works on a copy. Some modifications
> by themselves can cause constraint violations or data loss due to ambiguity
> in how the changes should be applied or the order in which they are executed.
> In the worst-case scenario, you can use the output as a reference to write
> your own migration script.

[`sqlite_schema`]: https://sqlite.org/schematab.html
[ALTER TABLE]: https://sqlite.org/lang_altertable.html

## Usage

Assuming you have Python 3.8+ and Git, you can install this library with:

```sh
pip install git+https://github.com/thegamecracks/sqlitediff@v0.1.5
```

After installation, the command-line interface can be used with `sqlitediff`
or `python -m sqlitediff`. It can compare SQLite database files directly
or take .sql scripts which are executed in-memory before comparison.
Run [`sqlitediff --help`](/src/sqlitediff/__main__.py) for more information.

## License

This project is written under the [MIT] license.

[MIT]: /LICENSE
