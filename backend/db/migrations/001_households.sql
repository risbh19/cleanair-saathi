CREATE TABLE households (
    id uuid PRIMARY KEY,
    session_digest bytea UNIQUE NOT NULL,
    home jsonb NOT NULL
);

CREATE TABLE members (
    household_id uuid REFERENCES households ON DELETE CASCADE,
    position integer NOT NULL,
    age_band text NOT NULL,
    sensitive boolean NOT NULL,
    PRIMARY KEY (household_id, position)
);

CREATE TABLE commutes (
    household_id uuid NOT NULL,
    member_position integer NOT NULL,
    position integer NOT NULL,
    journey jsonb NOT NULL,
    PRIMARY KEY (household_id, member_position, position),
    FOREIGN KEY (household_id, member_position)
        REFERENCES members (household_id, position) ON DELETE CASCADE
);
