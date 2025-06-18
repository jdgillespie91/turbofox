PRAGMA page_size = 8192;
PRAGMA journal_mode = WAL;
PRAGMA auto_vacuum = INCREMENTAL;

-- schema_version
CREATE TABLE schema_version (
    id TEXT DEFAULT 'singleton' CHECK (id = 'singleton'),
    version INTEGER NOT NULL
);

INSERT INTO schema_version (id, version)
VALUES ('singleton', 1)
;