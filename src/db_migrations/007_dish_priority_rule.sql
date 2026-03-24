CREATE TABLE IF NOT EXISTS dish_priority_rule (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  dish_id INTEGER NOT NULL,
  weekday INTEGER NULL,   -- 0=lun ... 5=sab; NULL = cualquier día
  slot TEXT NULL,         -- slot específico; NULL = cualquier slot compatible
  weight INTEGER NOT NULL DEFAULT 10,
  note TEXT NULL,
  UNIQUE(dish_id, weekday, slot),
  FOREIGN KEY (dish_id) REFERENCES dish(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_dish_priority_rule_lookup
  ON dish_priority_rule(dish_id, weekday, slot);
