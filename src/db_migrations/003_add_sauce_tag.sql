-- Migration 003: Add sauce_tag column to dish table
-- sauce_tag groups dishes that share the same sauce/flavor profile
-- so the rotation engine can avoid repeating the same sauce within the window.

ALTER TABLE dish ADD COLUMN sauce_tag TEXT DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_dish_sauce_tag ON dish(sauce_tag);
