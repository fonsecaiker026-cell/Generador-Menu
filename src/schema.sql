PRAGMA foreign_keys = ON;

-- =========================
-- Catálogo de platillos
-- =========================
CREATE TABLE IF NOT EXISTS dish (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  course_group TEXT NOT NULL, -- entrada_no_comal | sopa | crema | pasta | arroz | ensalada | fuerte | complemento | especial
  protein TEXT NOT NULL DEFAULT 'none', -- res | pollo | cerdo | pescado | camaron | none
  style_tag TEXT,   -- ej: "al_ajillo", "a_la_naranja" (identificador único por dish)
  sauce_tag TEXT,   -- ej: "salsa_chipotle", "mole_verde" (agrupa dishes con misma salsa para rotación cross-slot)
  active INTEGER NOT NULL DEFAULT 1
);

-- Regla extra para res: no repetir corte
CREATE TABLE IF NOT EXISTS beef_cut (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dish_beef_cut (
  dish_id INTEGER NOT NULL,
  beef_cut_id INTEGER NOT NULL,
  PRIMARY KEY (dish_id, beef_cut_id),
  FOREIGN KEY (dish_id) REFERENCES dish(id) ON DELETE CASCADE,
  FOREIGN KEY (beef_cut_id) REFERENCES beef_cut(id) ON DELETE CASCADE
);

-- Tags flexibles para días especiales / premium / fijos
CREATE TABLE IF NOT EXISTS dish_tag (
  dish_id INTEGER NOT NULL,
  tag TEXT NOT NULL, -- monday_molcajete, friday_required, friday_premium, saturday_fixed...
  PRIMARY KEY (dish_id, tag),
  FOREIGN KEY (dish_id) REFERENCES dish(id) ON DELETE CASCADE
);

-- Temporadas por platillo (BLOCK/WARN/ALLOW)
CREATE TABLE IF NOT EXISTS dish_season (
  dish_id INTEGER PRIMARY KEY,
  rule TEXT NOT NULL DEFAULT 'ALLOW', -- BLOCK | WARN | ALLOW
  start_month INTEGER, -- 1..12
  end_month INTEGER,   -- 1..12 (puede cruzar año)
  FOREIGN KEY (dish_id) REFERENCES dish(id) ON DELETE CASCADE
);

-- =========================
-- Menú semanal e historial
-- =========================
CREATE TABLE IF NOT EXISTS menu_week (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  week_start_date TEXT NOT NULL UNIQUE, -- YYYY-MM-DD (lunes)
  generated_at TEXT NOT NULL,
  finalized INTEGER NOT NULL DEFAULT 0,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS menu_item (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  menu_week_id INTEGER NOT NULL,
  menu_date TEXT NOT NULL, -- YYYY-MM-DD
  slot TEXT NOT NULL,      -- ej: fuerte_res, sopa, ensalada_A, etc.
  dish_id INTEGER NOT NULL,

  is_forced INTEGER NOT NULL DEFAULT 0,
  was_exception INTEGER NOT NULL DEFAULT 0,
  exception_reason TEXT,

  explanation TEXT,

  FOREIGN KEY (menu_week_id) REFERENCES menu_week(id) ON DELETE CASCADE,
  FOREIGN KEY (dish_id) REFERENCES dish(id) ON DELETE RESTRICT,

  UNIQUE(menu_date, slot)
);

-- Bloqueos / forzados del dueño (rango)
CREATE TABLE IF NOT EXISTS dish_lock (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  dish_id INTEGER NOT NULL,
  lock_type TEXT NOT NULL, -- BLOCK | FORCE
  start_date TEXT,
  end_date TEXT,
  reason TEXT,
  FOREIGN KEY (dish_id) REFERENCES dish(id) ON DELETE CASCADE
);

-- Sobrantes (solo sugerencias)
CREATE TABLE IF NOT EXISTS leftover (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL,
  protein TEXT NOT NULL,
  quantity REAL NOT NULL,
  unit TEXT NOT NULL,
  note TEXT
);
