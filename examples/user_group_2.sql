-- This is an example script to show how sqlitediff works.
-- Try it out by running:
-- sqlitediff examples/user_group_1.sql examples/user_group_2.sql

-- Updated user name constraint
CREATE TABLE user (id INTEGER PRIMARY KEY, name TEXT NOT NULL);

-- Added group description column
CREATE TABLE "group" (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT ''
);

CREATE TABLE user_group (
    user_id INTEGER REFERENCES user (id),
    group_id INTEGER REFERENCES "group" (id),
    PRIMARY KEY (user_id, group_id)
);

-- Added index for group users
CREATE INDEX ix_group_user ON user_group (group_id, user_id);

-- Changed index to include ID
CREATE INDEX ix_user_name ON user (name, id);

-- Changed kawaii group to ID 2, changing triggers/views
INSERT INTO "group" (id, name) VALUES (2, 'kawaii');
CREATE TRIGGER add_user_to_kawaii_group
    INSERT ON user
    BEGIN
        INSERT INTO user_group (user_id, group_id) VALUES (new.id, 2);
    END;

CREATE VIEW user_group_kawaii (id) AS
    SELECT user_id FROM user_group WHERE group_id = 2;

-- Added 'all' group as ID 1 with new trigger/view
INSERT INTO "group" (id, name) VALUES (1, 'all');
CREATE TRIGGER add_user_to_all_group
    INSERT ON user
    BEGIN
        INSERT INTO user_group (user_id, group_id) VALUES (new.id, 1);
    END;

CREATE VIEW user_group_all (id) AS
    SELECT user_id FROM user_group WHERE group_id = 1;
