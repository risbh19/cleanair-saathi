CREATE TABLE school_run_offers (
    household_id uuid PRIMARY KEY REFERENCES households ON DELETE CASCADE,
    group_digest bytea NOT NULL,
    locality_key text NOT NULL,
    departure_slot smallint NOT NULL CHECK (departure_slot BETWEEN 0 AND 95),
    expires_on date NOT NULL
);
CREATE INDEX school_run_group ON school_run_offers(group_digest, locality_key, departure_slot, expires_on);
