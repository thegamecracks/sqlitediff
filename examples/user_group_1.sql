-- This is an example script to show how sqlitediff works.
-- Try it out by running:
-- sqlitediff examples/user_group_1.sql examples/user_group_2.sql
CREATE TABLE user (id INTEGER PRIMARY KEY, name TEXT); -- Add NOT NULL to name later
CREATE TABLE "group" (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE user_group (
    user_id INTEGER REFERENCES user (id),
    group_id INTEGER REFERENCES "group" (id),
    PRIMARY KEY (user_id, group_id)
);

CREATE INDEX ix_user_name ON user (name);

INSERT INTO "group" (id, name) VALUES (1, 'kawaii');
CREATE TRIGGER add_user_to_kawaii_group
    INSERT ON user
    BEGIN
        INSERT INTO user_group (user_id, group_id) VALUES (new.id, 1);
    END;

CREATE VIEW user_group_kawaii (id) AS
    SELECT user_id FROM user_group WHERE group_id = 1;
