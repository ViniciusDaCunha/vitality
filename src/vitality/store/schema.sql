CREATE TABLE commits (
    commit_hash   TEXT NOT NULL,
    author        TEXT NOT NULL,
    committed_at  TEXT NOT NULL,
    file_path     TEXT NOT NULL,
    PRIMARY KEY (commit_hash, file_path)
);

CREATE TABLE declared_dependencies (
    name          TEXT PRIMARY KEY,
    version_spec  TEXT,
    source_file   TEXT NOT NULL
);

CREATE TABLE runtime_calls (
    symbol        TEXT NOT NULL,
    call_count    INTEGER NOT NULL DEFAULT 0,
    last_scan_id  TEXT NOT NULL,
    PRIMARY KEY (symbol, last_scan_id)
);

CREATE TABLE scans (
    scan_id     TEXT PRIMARY KEY,
    started_at  TEXT NOT NULL,
    finished_at TEXT
);
