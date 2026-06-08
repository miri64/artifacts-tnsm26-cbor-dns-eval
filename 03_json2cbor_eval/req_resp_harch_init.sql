PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS objects (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL,
    type TEXT NOT NULL,
    orig_len INTEGER NOT NULL,
    object BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS errors (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL,
    lib TEXT NOT NULL,
    error TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS keys (
    id INTEGER PRIMARY KEY,
    obj_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    count INTEGER NOT NULL,
    FOREIGN KEY (obj_id)
       REFERENCES objects (id)
);
CREATE TABLE IF NOT EXISTS special_values (
    id INTEGER PRIMARY KEY,
    key_id INTEGER NOT NULL,
    value TEXT NOT NULL,
    count INTEGER NOT NULL,
    FOREIGN KEY (key_id)
       REFERENCES keys (id)
);
CREATE INDEX IF NOT EXISTS url_idx ON objects(url);
CREATE INDEX IF NOT EXISTS error_idx ON errors(url);
