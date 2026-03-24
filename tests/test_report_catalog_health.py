from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src import db
from src.engine.generator import DISH_ID_ANTOJITOS_COMAL, DISH_ID_ARROZ_AL_GUSTO
from src.engine.report import catalog_health_report


class CatalogHealthReportTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="menu_restaurante_catalog_health_")
        self.old_db_path = db.DB_PATH
        db.DB_PATH = Path(self.tmpdir) / "catalog_health.db"
        db.init_db()

    def tearDown(self) -> None:
        db.DB_PATH = self.old_db_path
        self.tmpdir = None

    def test_overused_ignores_fixed_slots(self) -> None:
        with db.get_conn() as conn:
            conn.execute(
                """
                INSERT INTO dish(id, name, course_group, protein, style_tag, active)
                VALUES (?, 'Antojitos del Comal', 'entrada_no_comal', 'none', NULL, 1)
                """,
                (DISH_ID_ANTOJITOS_COMAL,),
            )
            conn.execute(
                """
                INSERT INTO dish(id, name, course_group, protein, style_tag, active)
                VALUES (?, 'Arroz al gusto', 'arroz', 'none', NULL, 1)
                """,
                (DISH_ID_ARROZ_AL_GUSTO,),
            )
            conn.execute(
                """
                INSERT INTO dish(id, name, course_group, protein, style_tag, active)
                VALUES (3001, 'Crema poblana', 'crema', 'none', NULL, 1)
                """
            )
            conn.execute(
                """
                INSERT INTO menu_week(week_start_date, generated_at, finalized, notes)
                VALUES ('2026-03-09', '2026-03-09T08:00:00', 0, NULL)
                """
            )
            week_id = int(
                conn.execute(
                    "SELECT id FROM menu_week WHERE week_start_date='2026-03-09'"
                ).fetchone()["id"]
            )
            for i in range(12):
                day = 9 + i
                menu_date = f"2026-03-{day:02d}"
                conn.execute(
                    """
                    INSERT INTO menu_item(menu_week_id, menu_date, slot, dish_id, is_forced, was_exception, exception_reason, explanation)
                    VALUES (?, ?, 'entrada_comal', ?, 1, 0, NULL, NULL)
                    """,
                    (week_id, menu_date, DISH_ID_ANTOJITOS_COMAL),
                )
                conn.execute(
                    """
                    INSERT INTO menu_item(menu_week_id, menu_date, slot, dish_id, is_forced, was_exception, exception_reason, explanation)
                    VALUES (?, ?, 'arroz', ?, 1, 0, NULL, NULL)
                    """,
                    (week_id, menu_date, DISH_ID_ARROZ_AL_GUSTO),
                )
                conn.execute(
                    """
                    INSERT INTO menu_item(menu_week_id, menu_date, slot, dish_id, is_forced, was_exception, exception_reason, explanation)
                    VALUES (?, ?, 'crema', 3001, 0, 0, NULL, NULL)
                    """,
                    (week_id, menu_date),
                )
            conn.commit()

        report = catalog_health_report(since_days=60, max_uses_warn=11)
        overused_ids = {int(row["id"]) for row in report["overused"]}

        self.assertIn(3001, overused_ids)
        self.assertNotIn(DISH_ID_ANTOJITOS_COMAL, overused_ids)
        self.assertNotIn(DISH_ID_ARROZ_AL_GUSTO, overused_ids)


if __name__ == "__main__":
    unittest.main()
