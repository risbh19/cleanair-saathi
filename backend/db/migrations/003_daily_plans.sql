CREATE TABLE daily_plans (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    household_id uuid NOT NULL REFERENCES households ON DELETE CASCADE,
    plan_date date NOT NULL,
    data_mode text NOT NULL,
    band_used text,
    as_of timestamptz,
    UNIQUE (household_id, plan_date, data_mode)
);

CREATE TABLE plan_items (
    id uuid PRIMARY KEY,
    plan_id bigint NOT NULL REFERENCES daily_plans ON DELETE CASCADE,
    position integer NOT NULL,
    card jsonb NOT NULL,
    status text NOT NULL DEFAULT 'planned' CHECK (status IN ('planned', 'done', 'skipped')),
    UNIQUE (plan_id, position)
);
