CREATE TABLE IF NOT EXISTS menu_closed_day (
  menu_week_id INTEGER NOT NULL,
  menu_date TEXT NOT NULL,
  reason TEXT,
  PRIMARY KEY (menu_week_id, menu_date),
  FOREIGN KEY (menu_week_id) REFERENCES menu_week(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_menu_closed_day_date
  ON menu_closed_day(menu_date);
