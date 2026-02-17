-- Shared DB schema for all frameworks.
-- Applied by the postgres container on startup.

CREATE TABLE IF NOT EXISTS items (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    description TEXT DEFAULT '',
    price       NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Seed 1000 rows for db-read benchmarks
INSERT INTO items (name, description, price)
SELECT
    'item-' || gs,
    'Description for item ' || gs || '. Lorem ipsum dolor sit amet.',
    ROUND((RANDOM() * 999 + 1)::numeric, 2)
FROM generate_series(1, 1000) AS gs
ON CONFLICT DO NOTHING;
