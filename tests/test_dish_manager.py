from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src import db
from src.engine import dish_manager


def _apply_test_schema() -> None:
    db.init_db()


def _insert_dish(
    name: str,
    course_group: str = "sopa",
    protein: str = "none",
    style_tag: str | None = None,
    active: int = 1,
    *,
    dish_id: int | None = None,
) -> int:
    with db.get_conn() as conn:
        dish_manager._ensure_sauce_tag_column(conn)
        if dish_id is None:
            cur = conn.execute(
                """
                INSERT INTO dish(name, course_group, protein, style_tag, sauce_tag, active)
                VALUES (?, ?, ?, ?, NULL, ?)
                """,
                (name, course_group, protein, style_tag, int(active)),
            )
            conn.commit()
            return int(cur.lastrowid)

        conn.execute(
            """
            INSERT INTO dish(id, name, course_group, protein, style_tag, sauce_tag, active)
            VALUES (?, ?, ?, ?, ?, NULL, ?)
            """,
            (int(dish_id), name, course_group, protein, style_tag, int(active)),
        )
        conn.commit()
        return int(dish_id)


class DishManagerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="menu_restaurante_test_")
        self.old_db_path = db.DB_PATH
        db.DB_PATH = Path(self.tmpdir) / "test.db"
        _apply_test_schema()

    def tearDown(self) -> None:
        db.DB_PATH = self.old_db_path
        self.tmpdir = None

    def test_init_db_bootstraps_schema_and_migrations(self) -> None:
        with db.get_conn() as conn:
            menu_override = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='menu_override'"
            ).fetchone()
            sauce_tag = conn.execute("PRAGMA table_info(dish)").fetchall()

        self.assertIsNotNone(menu_override)
        self.assertIn("sauce_tag", {str(r["name"]) for r in sauce_tag})

    def test_create_and_update_dish(self) -> None:
        dish_id = dish_manager.create_dish(
            name="Pollo en salsa verde",
            course_group="fuerte",
            protein="pollo",
            style_tag="salsa_verde",
            sauce_tag="verde",
            tags=["daily", "pollo"],
        )

        detail = dish_manager.dish_detail(dish_id)
        self.assertEqual(detail["dish"]["name"], "Pollo en salsa verde")
        self.assertEqual(detail["dish"]["sauce_tag"], "verde")
        self.assertEqual(detail["tags"], ["daily", "pollo"])

        updated = dish_manager.update_dish(
            dish_id,
            name="Pollo en salsa roja",
            sauce_tag="roja",
            tags=["especial"],
            active=1,
        )
        self.assertEqual(updated["dish"]["name"], "Pollo en salsa roja")
        self.assertEqual(updated["dish"]["sauce_tag"], "roja")
        self.assertEqual(updated["tags"], ["especial"])

    def test_create_rejects_monday_molcajete_without_protein(self) -> None:
        with self.assertRaisesRegex(ValueError, "monday_molcajete"):
            dish_manager.create_dish(
                name="Molcajete invalido",
                course_group="fuerte",
                protein="none",
                style_tag="molcajete_invalido",
                sauce_tag=None,
                tags=["monday_molcajete"],
            )

    def test_update_rejects_adding_monday_molcajete_tag_without_protein(self) -> None:
        dish_id = dish_manager.create_dish(
            name="Molcajete base",
            course_group="fuerte",
            protein="none",
            style_tag="molcajete_base",
            sauce_tag=None,
            tags=[],
        )
        with self.assertRaisesRegex(ValueError, "monday_molcajete"):
            dish_manager.update_dish(dish_id, tags=["monday_molcajete"])

    def test_protein_aliases_map_to_pescado(self) -> None:
        dish_id = dish_manager.create_dish(
            name="Montadito de Atun Especial",
            course_group="entrada_no_comal",
            protein="atun",
            style_tag="montadito_de_atun_especial",
            sauce_tag=None,
            tags=[],
        )
        detail = dish_manager.dish_detail(dish_id)
        self.assertEqual(detail["dish"]["protein"], "pescado")

    def test_deactivate_dish_rejects_future_overrides(self) -> None:
        dish_id = _insert_dish("Crema poblana", course_group="crema")
        with db.get_conn() as conn:
            conn.execute(
                """
                INSERT INTO menu_override(menu_date, slot, forced_dish_id, blocked_dish_id, note)
                VALUES (date('now', '+3 day'), 'crema', ?, NULL, 'test')
                """,
                (dish_id,),
            )
            conn.commit()

        with self.assertRaisesRegex(ValueError, "overrides futuros activos"):
            dish_manager.deactivate_dish(dish_id)

    def test_merge_dishes_reassigns_references(self) -> None:
        keep_id = _insert_dish("Pasta Alfredo", course_group="pasta", style_tag="alfredo")
        delete_id = _insert_dish("Pasta Alfredo Duplicada", course_group="pasta", style_tag="alfredo_dup")

        with db.get_conn() as conn:
            conn.execute("INSERT INTO dish_tag(dish_id, tag) VALUES (?, ?)", (keep_id, "keep"))
            conn.execute("INSERT INTO dish_tag(dish_id, tag) VALUES (?, ?)", (delete_id, "dup"))
            conn.execute(
                """
                INSERT INTO menu_week(week_start_date, generated_at, finalized, notes)
                VALUES ('2026-03-02', '2026-03-02T10:00:00', 0, NULL)
                """
            )
            week_id = conn.execute("SELECT id FROM menu_week WHERE week_start_date='2026-03-02'").fetchone()["id"]
            conn.execute(
                """
                INSERT INTO menu_item(menu_week_id, menu_date, slot, dish_id, is_forced, was_exception, exception_reason, explanation)
                VALUES (?, '2026-03-03', 'pasta', ?, 0, 0, NULL, NULL)
                """,
                (int(week_id), delete_id),
            )
            conn.execute(
                """
                INSERT INTO menu_override(menu_date, slot, forced_dish_id, blocked_dish_id, note)
                VALUES ('2026-03-10', 'pasta', ?, ?, 'merge')
                """,
                (delete_id, delete_id),
            )
            conn.commit()

        dish_manager.merge_dishes(keep_id, delete_id)

        with db.get_conn() as conn:
            merged_item = conn.execute("SELECT dish_id FROM menu_item WHERE slot='pasta'").fetchone()
            merged_override = conn.execute(
                "SELECT forced_dish_id, blocked_dish_id FROM menu_override WHERE slot='pasta'"
            ).fetchone()
            tags = conn.execute("SELECT tag FROM dish_tag WHERE dish_id=? ORDER BY tag", (keep_id,)).fetchall()
            deleted = conn.execute("SELECT 1 FROM dish WHERE id=?", (delete_id,)).fetchone()

        self.assertEqual(int(merged_item["dish_id"]), keep_id)
        self.assertEqual(int(merged_override["forced_dish_id"]), keep_id)
        self.assertEqual(int(merged_override["blocked_dish_id"]), keep_id)
        self.assertEqual([r["tag"] for r in tags], ["dup", "keep"])
        self.assertIsNone(deleted)

    def test_search_and_detail(self) -> None:
        fish_id = dish_manager.create_dish(
            name="Pescado al mojo",
            course_group="fuerte",
            protein="pescado",
            style_tag="mojo",
            sauce_tag="ajo",
            tags=["mar"],
        )
        dish_manager.create_dish(
            name="Pechuga asada",
            course_group="fuerte",
            protein="pollo",
            style_tag="asada",
            sauce_tag=None,
            tags=["plancha"],
        )

        with db.get_conn() as conn:
            conn.execute(
                """
                INSERT INTO menu_week(week_start_date, generated_at, finalized, notes)
                VALUES ('2026-02-23', '2026-02-23T08:00:00', 0, NULL)
                """
            )
            week_id = conn.execute("SELECT id FROM menu_week WHERE week_start_date='2026-02-23'").fetchone()["id"]
            conn.execute(
                """
                INSERT INTO menu_item(menu_week_id, menu_date, slot, dish_id, is_forced, was_exception, exception_reason, explanation)
                VALUES (?, date('now', '-10 day'), 'fuerte_pescado', ?, 0, 0, NULL, 'hist')
                """,
                (int(week_id), fish_id),
            )
            conn.execute(
                """
                INSERT INTO menu_override(menu_date, slot, forced_dish_id, blocked_dish_id, note)
                VALUES (date('now', '+5 day'), 'fuerte_pescado', ?, NULL, 'future')
                """,
                (fish_id,),
            )
            conn.commit()

        results = dish_manager.search_dishes(query="mojo", protein="pescado", sauce_tag="ajo", active=True)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], fish_id)
        self.assertEqual(results[0]["tags"], ["mar"])

        detail = dish_manager.dish_detail(fish_id)
        self.assertEqual(detail["dish"]["sauce_tag"], "ajo")
        self.assertEqual(len(detail["usage_history_60d"]), 1)
        self.assertEqual(len(detail["upcoming_overrides"]), 1)

    def test_find_duplicate_groups_groups_by_canonical_name_group_and_protein(self) -> None:
        d1 = _insert_dish("Albóndigas al Chipotle", course_group="fuerte", protein="res")
        d2 = _insert_dish("Albondigas al chipotle", course_group="fuerte", protein="res")
        _insert_dish("Albondigas al chipotle (pollo)", course_group="fuerte", protein="pollo")

        groups = dish_manager.find_duplicate_groups(include_inactive=True)
        target = [g for g in groups if d1 in [g["keep_id"], *g["drop_ids"]] or d2 in [g["keep_id"], *g["drop_ids"]]]
        self.assertEqual(len(target), 1)
        self.assertEqual(target[0]["course_group"], "fuerte")
        self.assertEqual(target[0]["protein"], "res")
        self.assertEqual(target[0]["size"], 2)

    def test_deduplicate_dishes_apply_merges_references(self) -> None:
        keep_id = _insert_dish("Crema de Brocoli", course_group="crema", protein="none")
        dup_id = _insert_dish("Crema de Brócoli", course_group="crema", protein="none")

        with db.get_conn() as conn:
            conn.execute("INSERT INTO dish_tag(dish_id, tag) VALUES (?, 'dup_tag')", (dup_id,))
            conn.execute(
                """
                INSERT INTO menu_week(week_start_date, generated_at, finalized, notes)
                VALUES ('2026-03-02', '2026-03-02T10:00:00', 0, NULL)
                """
            )
            week_id = int(conn.execute("SELECT id FROM menu_week WHERE week_start_date='2026-03-02'").fetchone()["id"])
            conn.execute(
                """
                INSERT INTO menu_item(menu_week_id, menu_date, slot, dish_id, is_forced, was_exception, exception_reason, explanation)
                VALUES (?, '2026-03-03', 'crema', ?, 0, 0, NULL, NULL)
                """,
                (week_id, dup_id),
            )
            conn.execute(
                """
                INSERT INTO menu_override(menu_date, slot, forced_dish_id, blocked_dish_id, note)
                VALUES ('2026-03-10', 'crema', ?, ?, 'dup')
                """,
                (dup_id, dup_id),
            )
            conn.commit()

        preview = dish_manager.deduplicate_dishes(apply=False, include_inactive=True)
        self.assertGreaterEqual(int(preview["groups_count"]), 1)

        applied = dish_manager.deduplicate_dishes(apply=True, include_inactive=True)
        self.assertGreaterEqual(int(applied["merged_count"]), 1)

        with db.get_conn() as conn:
            still_dup = conn.execute("SELECT 1 FROM dish WHERE id=?", (dup_id,)).fetchone()
            merged_item = conn.execute("SELECT dish_id FROM menu_item WHERE slot='crema'").fetchone()
            merged_override = conn.execute(
                "SELECT forced_dish_id, blocked_dish_id FROM menu_override WHERE slot='crema'"
            ).fetchone()
            tags = conn.execute("SELECT tag FROM dish_tag WHERE dish_id=? ORDER BY tag", (keep_id,)).fetchall()

        self.assertIsNone(still_dup)
        self.assertEqual(int(merged_item["dish_id"]), keep_id)
        self.assertEqual(int(merged_override["forced_dish_id"]), keep_id)
        self.assertEqual(int(merged_override["blocked_dish_id"]), keep_id)
        self.assertIn("dup_tag", [r["tag"] for r in tags])


if __name__ == "__main__":
    unittest.main()
