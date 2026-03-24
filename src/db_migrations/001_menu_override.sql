CREATE TABLE IF NOT EXISTS menu_override (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  menu_date TEXT NOT NULL,
  slot TEXT NOT NULL,
  forced_dish_id INTEGER NULL,
  note TEXT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(menu_date, slot),
  FOREIGN KEY (forced_dish_id) REFERENCES dish(id)
);
