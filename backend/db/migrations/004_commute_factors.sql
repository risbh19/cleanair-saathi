CREATE TABLE emission_factors (
    mode text PRIMARY KEY,
    grams_co2_per_km numeric NOT NULL CHECK (grams_co2_per_km > 0),
    basis text NOT NULL CHECK (basis IN ('vehicle', 'passenger')),
    vintage smallint NOT NULL,
    source_url text NOT NULL CHECK (source_url LIKE 'https://_%')
);

INSERT INTO emission_factors (mode, grams_co2_per_km, basis, vintage, source_url)
SELECT mode, grams, basis, 2015,
       'https://shaktifoundation.in/wp-content/uploads/2021/12/WRI-2015-India-Specific-Road-Transport-Emission-Factors.pdf'
FROM (VALUES
    ('petrol_hatchback_lt1000cc', 127, 'vehicle'),
    ('scooter_lt110cc', 36.8, 'vehicle'),
    ('cng_auto', 107.68, 'vehicle'),
    ('intracity_bus', 15.161, 'passenger')
) AS factors(mode, grams, basis);
