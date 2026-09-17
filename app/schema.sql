CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    done BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'done', 'failed')),
    processing BOOLEAN NOT NULL DEFAULT FALSE,
    result TEXT,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO tasks (title, done)
SELECT seed.title, seed.done
FROM (
    VALUES
        ('Buy milk', FALSE),
        ('Read a book', TRUE),
        ('Write some code', FALSE)
) AS seed(title, done)
WHERE NOT EXISTS (SELECT 1 FROM tasks);
