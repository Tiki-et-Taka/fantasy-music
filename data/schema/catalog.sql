-- Fantasy Music — catalogue figé (SQLite)
-- Spec : docs/09-schema-donnees.md
-- Hors périmètre : marché, groupes fantasy, auth joueur (voir commentaires en bas).

PRAGMA foreign_keys = ON;

CREATE TABLE series (
  id          TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  size        INTEGER NOT NULL CHECK (size > 0),
  released_at TEXT,                    -- ISO date YYYY-MM-DD, nullable
  status      TEXT NOT NULL DEFAULT 'draft'
              CHECK (status IN ('draft', 'released', 'archived'))
);

CREATE TABLE artist (
  qid         TEXT PRIMARY KEY,        -- Wikidata Q-id
  mbid        TEXT,                    -- MusicBrainz artist UUID
  name        TEXT NOT NULL,
  sex         TEXT CHECK (sex IS NULL OR sex IN ('f', 'm', 'x')),
  instrument  TEXT
);

CREATE TABLE "group" (
  mbid        TEXT PRIMARY KEY,        -- MusicBrainz
  name        TEXT NOT NULL,
  qid         TEXT                     -- Wikidata du groupe, nullable
);

CREATE TABLE membership (
  artist_qid  TEXT NOT NULL REFERENCES artist(qid),
  group_mbid  TEXT NOT NULL REFERENCES "group"(mbid),
  start       TEXT,                    -- ISO date
  "end"       TEXT,
  is_primary  INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),
  PRIMARY KEY (artist_qid, group_mbid)
);

CREATE TABLE plate (
  id          TEXT PRIMARY KEY,        -- ex. encre|voix|4|1970s80s|stade|m
  style       TEXT NOT NULL
              CHECK (style IN ('serigraphie', 'contrejour', 'encre')),
  instrument  TEXT NOT NULL,
  pose        INTEGER NOT NULL CHECK (pose BETWEEN 1 AND 7),
  costume     TEXT NOT NULL,
  venue       TEXT NOT NULL,
  sil         TEXT NOT NULL CHECK (sil IN ('f', 'm', 'x')),
  path        TEXT
);

-- Ordre des paliers (utilisé par triggers / app) : commune < argent < or < platine < diamant
CREATE TABLE card (
  id              TEXT PRIMARY KEY,    -- {series_id}:{qid}
  series_id       TEXT NOT NULL REFERENCES series(id),
  artist_qid      TEXT NOT NULL REFERENCES artist(qid),
  rank_in_series  INTEGER NOT NULL CHECK (rank_in_series > 0),
  rank_vivier     INTEGER,
  rarity_initial  TEXT NOT NULL
                  CHECK (rarity_initial IN (
                    'commune', 'argent', 'or', 'platine', 'diamant'
                  )),
  rarity_current  TEXT NOT NULL
                  CHECK (rarity_current IN (
                    'commune', 'argent', 'or', 'platine', 'diamant'
                  )),
  family          TEXT NOT NULL,
  band            TEXT NOT NULL,
  region          TEXT,
  era             TEXT,
  motif           TEXT,
  plate_id        TEXT NOT NULL REFERENCES plate(id),
  group_mbid      TEXT REFERENCES "group"(mbid),
  in_booster_pool INTEGER NOT NULL DEFAULT 1 CHECK (in_booster_pool IN (0, 1)),
  UNIQUE (series_id, artist_qid),
  UNIQUE (series_id, rank_in_series)
);

CREATE TABLE rarity_event (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  card_id          TEXT NOT NULL REFERENCES card(id),
  from_rarity      TEXT NOT NULL
                   CHECK (from_rarity IN (
                     'commune', 'argent', 'or', 'platine', 'diamant'
                   )),
  to_rarity        TEXT NOT NULL
                   CHECK (to_rarity IN (
                     'commune', 'argent', 'or', 'platine', 'diamant'
                   )),
  series_boundary  TEXT NOT NULL,     -- série / fenêtre déclenchante
  effective_at     TEXT NOT NULL,     -- ISO date
  reason           TEXT NOT NULL,
  CHECK (from_rarity <> to_rarity)
);

CREATE INDEX idx_card_series_rarity ON card(series_id, rarity_current);
CREATE INDEX idx_card_pool ON card(series_id, in_booster_pool);
CREATE INDEX idx_rarity_event_card ON rarity_event(card_id);
CREATE INDEX idx_membership_group ON membership(group_mbid);

-- ---------------------------------------------------------------------------
-- Appendice joueur (futur Neon) — non créé ici ; référence docs/09-schema-donnees.md
--
-- owned_copy(user_id, card_id → card.id, qty, acquired_at, fresh)
-- wallet(user_id PK, credits, packs, last_daily, starter)
-- ---------------------------------------------------------------------------
