# sqlitediff

![](https://img.shields.io/github/actions/workflow/status/thegamecracks/sqlitediff/pyright-lint.yml?style=flat-square&label=lint)
![](https://img.shields.io/github/actions/workflow/status/thegamecracks/sqlitediff/python-test.yml?style=flat-square&logo=pytest&label=tests)

A command-line program for generating SQLite schema diffs.

```sql
$ sqlitediff examples/user_group_1.sql examples/user_group_2.sql
PRAGMA foreign_keys = off;
BEGIN TRANSACTION;

-- Modified Objects --

-- Previous table schema for user:
-- CREATE TABLE user (id INTEGER PRIMARY KEY, name TEXT);
ALTER TABLE user RENAME TO sqlitediff_temp;
CREATE TABLE user (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
INSERT INTO user (id, name) SELECT * FROM sqlitediff_temp;
DROP TABLE sqlitediff_temp;

-- Previous index schema for ix_user_name:
-- CREATE INDEX ix_user_name ON user (name);
DROP INDEX ix_user_name;
CREATE INDEX ix_user_name ON user (name, id);

-- Previous view schema for user_group_kawaii:
-- CREATE VIEW user_group_kawaii (id) AS
--     SELECT user_id FROM user_group WHERE group_id = 1;
DROP VIEW user_group_kawaii;
CREATE VIEW user_group_kawaii (id) AS
    SELECT user_id FROM user_group WHERE group_id = 2;

-- Previous trigger schema for add_user_to_kawaii_group:
-- CREATE TRIGGER add_user_to_kawaii_group
--     INSERT ON user
--     BEGIN
--         INSERT INTO user_group (user_id, group_id) VALUES (new.id, 1);
--     END;
DROP TRIGGER add_user_to_kawaii_group;
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

COMMIT;
PRAGMA foreign_keys = off; -- As initially configured by database
```

> [!NOTE]
>
> This project is not associated with [5f.0](https://github.com/5f0ne)'s
> PyPI package, [sqlitediff](https://pypi.org/project/sqlitediff/),
> which caters towards analysis of data changes in an SQLite database.

## Usage

Assuming you have Python 3.8+ and Git, you can install this library with:

```sh
pip install git+https://github.com/thegamecracks/sqlitediff
```

After installation, the command-line interface can be used with `sqlitediff`
or `python -m sqlitediff`. It can compare SQLite database files directly
or take .sql scripts which are executed in-memory before comparison.
See [`sqlitediff --help`](/src/sqlitediff/__main__.py) for more information.

## License

This project is written under the [MIT] license.

[MIT]: /LICENSE
