-- SQLite: create FTS5 table and triggers
CREATE VIRTUAL TABLE IF NOT EXISTS gigs_fts USING fts5(title, description, content='gigs', content_rowid='id');
CREATE TRIGGER IF NOT EXISTS gigs_ai AFTER INSERT ON gigs BEGIN
    INSERT INTO gigs_fts(rowid, title, description) VALUES (new.id, new.title, new.description);
END;
CREATE TRIGGER IF NOT EXISTS gigs_ad AFTER DELETE ON gigs BEGIN
    INSERT INTO gigs_fts(gigs_fts, rowid, title, description) VALUES('delete', old.id, old.title, old.description);
END;
CREATE TRIGGER IF NOT EXISTS gigs_au AFTER UPDATE ON gigs BEGIN
    INSERT INTO gigs_fts(gigs_fts, rowid, title, description) VALUES('delete', old.id, old.title, old.description);
    INSERT INTO gigs_fts(rowid, title, description) VALUES (new.id, new.title, new.description);
END;

-- Postgres: generated tsvector column and index
ALTER TABLE gigs ADD COLUMN IF NOT EXISTS search_tsv tsvector GENERATED ALWAYS AS (
  to_tsvector('english', coalesce(title,'') || ' ' || coalesce(description,''))
) STORED;
CREATE INDEX IF NOT EXISTS gigs_search_idx ON gigs USING GIN (search_tsv);
