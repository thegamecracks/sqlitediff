-- Table: images
CREATE TABLE images (
    id         INTEGER PRIMARY KEY,
    image_path TEXT    NOT NULL
);

-- Table: tag_values
CREATE TABLE tag_values (
    image_id INTEGER,
    tag_id   INTEGER,
    value    TEXT    NOT NULL,
    PRIMARY KEY (
        image_id,
        tag_id
    ),
    FOREIGN KEY (
        image_id
    )
    REFERENCES images (id) ON DELETE CASCADE,
    FOREIGN KEY (
        tag_id
    )
    REFERENCES tags (id) ON DELETE CASCADE
);

-- Table: tags
CREATE TABLE tags (
    id       INTEGER PRIMARY KEY,
    tag_name TEXT    NOT NULL
                     UNIQUE
);
