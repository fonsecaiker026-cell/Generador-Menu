from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import api_server
from src import db


def _apply_test_schema() -> None:
    db.init_db()


def _insert_dish(
    dish_id: int,
    name: str,
    course_group: str,
    protein: str = "none",
    style_tag: str | None = None,
    *,
    tags: list[str] | None = None,
) -> None:
    with db.get_conn() as conn:
        conn.execute(
            """
            INSERT INTO dish(id, name, course_group, protein, style_tag, active)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (dish_id, name, course_group, protein, style_tag),
        )
        for tag in tags or []:
            conn.execute("INSERT INTO dish_tag(dish_id, tag) VALUES (?, ?)", (dish_id, tag))
        conn.commit()


def _seed_minimum_catalog() -> None:
    _insert_dish(202, "Antojitos del comal", "entrada_no_comal")
    _insert_dish(1596, "Arroz al gusto", "arroz")

    _insert_dish(1, "Entrada del dia", "entrada_no_comal")
    _insert_dish(2, "Sopa de verduras", "sopa")
    _insert_dish(3, "Crema de elote", "crema")
    _insert_dish(4, "Pasta tornillos rojos", "pasta", style_tag="roja")
    _insert_dish(5, "Pasta blanca", "pasta", style_tag="blanca")
    _insert_dish(6, "Ensalada verde", "ensalada")
    _insert_dish(7, "Ensalada mixta", "ensalada")
    _insert_dish(8, "Ensalada de codito", "ensalada")
    _insert_dish(9, "Guarnicion del dia", "complemento")

    _insert_dish(10, "Res asada", "fuerte", "res")
    _insert_dish(11, "Pollo rostizado", "fuerte", "pollo")
    _insert_dish(12, "Cerdo adobado", "fuerte", "cerdo")
    _insert_dish(13, "Filete empanizado", "fuerte", "pescado")
    _insert_dish(14, "Camaron al ajillo", "fuerte", "camaron")

    _insert_dish(15, "Molcajete de res", "fuerte", "res", tags=["monday_molcajete"])
    _insert_dish(16, "Chamorro pibil", "fuerte", "cerdo", tags=["friday_chamorro"])
    _insert_dish(17, "Enchiladas verdes", "fuerte", tags=["sat_enchiladas", "also_complemento"])
    _insert_dish(18, "Caldo de pollo", "sopa", "pollo", tags=["only_sat"])

    _insert_dish(19, "Paella", "especial", style_tag="paella_fija", tags=["saturday_fixed"])
    _insert_dish(20, "Nuggets de pollo", "especial", style_tag="nuggets_fijo", tags=["saturday_fixed"])
    _insert_dish(21, "Pancita", "sopa", style_tag="pancita_fija", tags=["saturday_fixed"])


class ApiE2ETestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="menu_restaurante_api_")
        self.old_db_path = db.DB_PATH
        self.old_api_db_path = api_server.db_module.DB_PATH

        db.DB_PATH = Path(self.tmpdir) / "api.db"
        api_server.db_module.DB_PATH = db.DB_PATH
        api_server.db_module._BOOTSTRAPPED_DB_PATHS.clear()

        _apply_test_schema()
        _seed_minimum_catalog()

    def tearDown(self) -> None:
        db.DB_PATH = self.old_db_path
        api_server.db_module.DB_PATH = self.old_api_db_path
        api_server.db_module._BOOTSTRAPPED_DB_PATHS.clear()
        self.tmpdir = None

    def test_week_generate_override_and_finalize_flow(self) -> None:
        with TestClient(api_server.app) as client:
            r_gen = client.post("/api/weeks/2026-03-02/generate")
            self.assertEqual(r_gen.status_code, 200)
            self.assertIn("week_id", r_gen.json())

            r_get = client.get("/api/weeks/2026-03-02")
            self.assertEqual(r_get.status_code, 200)
            week_data = r_get.json()
            self.assertIsNotNone(week_data["week"])
            self.assertGreater(len(week_data["rows"]), 0)

            r_override = client.post(
                "/api/overrides",
                json={
                    "menu_date": "2026-03-02",
                    "slot": "ensalada_A",
                    "forced_dish_id": 7,
                    "note": "api_e2e",
                },
            )
            self.assertEqual(r_override.status_code, 200)

            r_apply = client.post("/api/overrides/2026-03-02/ensalada_A/apply")
            self.assertEqual(r_apply.status_code, 200)

            r_after = client.get("/api/weeks/2026-03-02")
            rows = r_after.json()["rows"]
            mon = [x for x in rows if x["menu_date"] == "2026-03-02" and x["slot"] == "ensalada_A"][0]
            thu = [x for x in rows if x["menu_date"] == "2026-03-05" and x["slot"] == "ensalada_A"][0]
            self.assertEqual(mon["dish_id"], 7)
            self.assertEqual(thu["dish_id"], 7)

            r_clear = client.post("/api/weeks/2026-03-02/clear-overrides")
            self.assertEqual(r_clear.status_code, 200)
            body = r_clear.json()
            self.assertIn("cleared", body)
            self.assertIn("reapplied_ok", body)
            self.assertIn("reapplied_failed", body)
            self.assertIsInstance(body["reapplied_failed"], list)

            r_finalize = client.post(
                "/api/weeks/2026-03-02/finalize",
                json={"finalized": True, "notes": "api_e2e_ok"},
            )
            self.assertEqual(r_finalize.status_code, 200)
            self.assertTrue(r_finalize.json()["ok"])

    def test_updating_molcajete_protein_reconciles_monday_slots(self) -> None:
        with TestClient(api_server.app) as client:
            r_gen = client.post("/api/weeks/2026-03-02/generate")
            self.assertEqual(r_gen.status_code, 200)

            before = client.get("/api/weeks/2026-03-02").json()["rows"]
            monday_before = [x for x in before if x["menu_date"] == "2026-03-02"]
            before_slots = {x["slot"] for x in monday_before}
            self.assertIn("molcajete", before_slots)
            self.assertNotIn("fuerte_res", before_slots)  # molcajete base is res in seed

            r_update = client.put("/api/dishes/15", json={"protein": "cerdo"})
            self.assertEqual(r_update.status_code, 200)
            body = r_update.json()
            self.assertIn("molcajete_reconcile", body)
            self.assertGreaterEqual(int(body["molcajete_reconcile"]["affected_count"]), 1)

            after = client.get("/api/weeks/2026-03-02").json()["rows"]
            monday_after = [x for x in after if x["menu_date"] == "2026-03-02"]
            after_slots = {x["slot"] for x in monday_after}
            self.assertIn("fuerte_res", after_slots)
            self.assertNotIn("fuerte_cerdo", after_slots)

    def test_regenerate_day_endpoint_only_updates_target_day(self) -> None:
        with TestClient(api_server.app) as client:
            r_gen = client.post("/api/weeks/2026-03-02/generate")
            self.assertEqual(r_gen.status_code, 200)

            with db.get_conn() as conn:
                week_id = int(
                    conn.execute(
                        "SELECT id FROM menu_week WHERE week_start_date='2026-03-02'"
                    ).fetchone()["id"]
                )
                conn.execute(
                    """
                    UPDATE menu_item
                    SET explanation = 'SENTINEL_TUESDAY_API'
                    WHERE menu_week_id = ?
                      AND menu_date = '2026-03-03'
                      AND slot = 'pasta'
                    """,
                    (week_id,),
                )
                conn.execute(
                    """
                    UPDATE menu_item
                    SET explanation = 'BROKEN_WEDNESDAY_API'
                    WHERE menu_week_id = ?
                      AND menu_date = '2026-03-04'
                      AND slot = 'pasta'
                    """,
                    (week_id,),
                )
                conn.commit()

            r_regen = client.post("/api/weeks/2026-03-02/days/2026-03-04/regenerate")
            self.assertEqual(r_regen.status_code, 200)

            rows = r_regen.json()["rows"]
            tuesday_pasta = [x for x in rows if x["menu_date"] == "2026-03-03" and x["slot"] == "pasta"][0]
            wednesday_pasta = [x for x in rows if x["menu_date"] == "2026-03-04" and x["slot"] == "pasta"][0]

            self.assertEqual(tuesday_pasta["explanation"], "SENTINEL_TUESDAY_API")
            self.assertNotEqual(wednesday_pasta["explanation"], "BROKEN_WEDNESDAY_API")

    def test_set_dish_active_false_reconciles_existing_menu(self) -> None:
        with TestClient(api_server.app) as client:
            r_gen = client.post("/api/weeks/2026-03-02/generate")
            self.assertEqual(r_gen.status_code, 200)

            week_before = client.get("/api/weeks/2026-03-02").json()["rows"]
            monday_before = [x for x in week_before if x["menu_date"] == "2026-03-02"]
            target = [x for x in monday_before if x["slot"] == "pasta"][0]
            old_dish_id = int(target["dish_id"])
            old_slot = str(target["slot"])

            r_disable = client.patch(f"/api/dishes/{old_dish_id}/active", json={"active": False})
            self.assertEqual(r_disable.status_code, 200)
            self.assertIn("catalog_reconcile", r_disable.json())

            week_after = client.get("/api/weeks/2026-03-02").json()["rows"]
            monday_after = [x for x in week_after if x["menu_date"] == "2026-03-02"]
            same_slot = [x for x in monday_after if x["slot"] == old_slot][0]
            self.assertNotEqual(int(same_slot["dish_id"]), old_dish_id)

    def test_cannot_deactivate_last_structural_slot_candidate(self) -> None:
        with TestClient(api_server.app) as client:
            # Seed catalog has a single friday_chamorro dish (id=16)
            r = client.patch("/api/dishes/16/active", json={"active": False})
            self.assertEqual(r.status_code, 422)
            self.assertIn("slot chamorro", r.json().get("detail", "").lower())

    def test_update_preserves_structural_tags(self) -> None:
        with TestClient(api_server.app) as client:
            r = client.put("/api/dishes/15", json={"tags": []})  # id=15 has monday_molcajete in seed
            self.assertEqual(r.status_code, 200)
            tags = set(r.json().get("tags", []))
            self.assertIn("monday_molcajete", tags)


if __name__ == "__main__":
    unittest.main()
