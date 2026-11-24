ALTER TABLE daily_plans ADD COLUMN locality_key text;
-- Historical plans lack a reliable locality snapshot; keep these in personal totals only.
CREATE INDEX daily_plans_locality_week ON daily_plans (locality_key, data_mode, plan_date);
