CREATE TABLE IF NOT EXISTS movies (
    id         SERIAL PRIMARY KEY,
    title      TEXT        NOT NULL,
    genre      TEXT        NOT NULL DEFAULT 'Без жанру',
    watched    BOOLEAN     NOT NULL DEFAULT FALSE,
    added_by   TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    watched_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS groceries (
    id         SERIAL PRIMARY KEY,
    item       TEXT        NOT NULL,
    bought     BOOLEAN     NOT NULL DEFAULT FALSE,
    added_by   TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS meals (
    id         SERIAL PRIMARY KEY,
    dish       TEXT        NOT NULL,
    planned    TEXT,
    cooked     BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
