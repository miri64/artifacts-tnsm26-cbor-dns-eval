PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS keys (
    id INTEGER PRIMARY KEY,
    type TEXT NOT NULL,
    key TEXT NOT NULL,
    count INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS special_values (
    id INTEGER PRIMARY KEY,
    key_id INTEGER NOT NULL,
    value TEXT NOT NULL,
    count INTEGER NOT NULL,
    FOREIGN KEY (key_id)
       REFERENCES keys (id)
);
