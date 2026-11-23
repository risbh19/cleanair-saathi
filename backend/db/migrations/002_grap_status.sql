CREATE TABLE grap_status (
    effective_from timestamptz PRIMARY KEY,
    stage smallint NOT NULL CHECK (stage BETWEEN 0 AND 4),
    source_url text NOT NULL,
    entered_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);
