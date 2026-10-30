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

CREATE TABLE IF NOT EXISTS config (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- One row per registered group (via /setup); topics are set with /here.
CREATE TABLE IF NOT EXISTS chats (
    chat_id            BIGINT PRIMARY KEY,
    movies_topic_id    BIGINT,
    groceries_topic_id BIGINT
);

-- Lists are per group.
ALTER TABLE movies    ADD COLUMN IF NOT EXISTS chat_id BIGINT;
ALTER TABLE groceries ADD COLUMN IF NOT EXISTS chat_id BIGINT;
ALTER TABLE meals     ADD COLUMN IF NOT EXISTS chat_id BIGINT;
