from __future__ import annotations

import tempfile
import unittest
import random
from pathlib import Path

from src import db
from src.engine import generator
from src.engine import service


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


class EngineRulesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="menu_restaurante_engine_")
        self.old_db_path = db.DB_PATH
        db.DB_PATH = Path(self.tmpdir) / "engine.db"
        _apply_test_schema()
        _seed_minimum_catalog()

    def tearDown(self) -> None:
        db.DB_PATH = self.old_db_path
        self.tmpdir = None

    def test_generate_week_enforces_monday_molcajete_and_saturday_shape(self) -> None:
        week_id = service.generate_week("2026-03-02")
        self.assertGreater(week_id, 0)

        data = service.list_week("2026-03-02")
        rows = data["rows"]

        monday = [r for r in rows if r.menu_date == "2026-03-02"]
        monday_slots = {r.slot for r in monday}
        self.assertIn("molcajete", monday_slots)
        self.assertNotIn("fuerte_res", monday_slots)

        saturday = [r for r in rows if r.menu_date == "2026-03-07"]
        saturday_slots = {r.slot for r in saturday}
        self.assertIn("pancita", saturday_slots)
        self.assertIn("paella", saturday_slots)
        self.assertIn("nuggets", saturday_slots)
        self.assertIn("enchiladas", saturday_slots)
        self.assertNotIn("arroz", saturday_slots)
        self.assertNotIn("complemento", saturday_slots)

    def test_salad_override_propagates_to_linked_day(self) -> None:
        service.generate_week("2026-03-02")
        service.set_override("2026-03-02", "ensalada_A", forced_dish_id=7, note="force linked salad")
        service.apply_override_now("2026-03-02", "ensalada_A")

        data = service.list_week("2026-03-02")
        monday_salad = [r for r in data["rows"] if r.menu_date == "2026-03-02" and r.slot == "ensalada_A"][0]
        thursday_salad = [r for r in data["rows"] if r.menu_date == "2026-03-05" and r.slot == "ensalada_A"][0]

        self.assertEqual(monday_salad.dish_id, 7)
        self.assertEqual(thursday_salad.dish_id, 7)
        self.assertEqual(monday_salad.is_forced, 1)
        self.assertEqual(thursday_salad.is_forced, 1)

        with db.get_conn() as conn:
            overrides = conn.execute(
                "SELECT menu_date FROM menu_override WHERE slot='ensalada_A' ORDER BY menu_date"
            ).fetchall()
        self.assertEqual([r["menu_date"] for r in overrides], ["2026-03-02", "2026-03-05"])

    def test_friday_always_includes_chamorro_slot(self) -> None:
        data = service.generate_week("2026-03-02")
        self.assertGreater(data, 0)

        week = service.list_week("2026-03-02")
        friday_rows = [r for r in week["rows"] if r.menu_date == "2026-03-06"]
        friday_slots = {r.slot for r in friday_rows}

        self.assertIn("chamorro", friday_slots)

    def test_finalize_week_blocks_when_audit_finds_missing_slot(self) -> None:
        service.generate_week("2026-03-02")

        with db.get_conn() as conn:
            week_id = conn.execute(
                "SELECT id FROM menu_week WHERE week_start_date='2026-03-02'"
            ).fetchone()["id"]
            conn.execute(
                """
                DELETE FROM menu_item
                WHERE menu_week_id = ?
                  AND menu_date = '2026-03-04'
                  AND slot = 'crema'
                """,
                (int(week_id),),
            )
            conn.commit()

        with self.assertRaisesRegex(RuntimeError, "No se puede finalizar la semana"):
            service.finalize_week("2026-03-02", finalized=True, notes="should_fail")

    def test_finalize_week_allows_valid_week(self) -> None:
        service.generate_week("2026-03-02")
        service.finalize_week("2026-03-02", finalized=True, notes="ok")

        data = service.list_week("2026-03-02")
        self.assertEqual(int(data["week"]["finalized"]), 1)

    def test_finalize_week_blocks_when_strict_score_below_threshold(self) -> None:
        service.generate_week("2026-03-02")
        original = service.FINALIZE_MIN_STRICT_SCORE
        original_min_active = service.FINALIZE_MIN_ACTIVE_DISHES_FOR_HARD_GATE
        service.FINALIZE_MIN_STRICT_SCORE = 101
        service.FINALIZE_MIN_ACTIVE_DISHES_FOR_HARD_GATE = 0
        try:
            with self.assertRaisesRegex(RuntimeError, "score estricto"):
                service.finalize_week("2026-03-02", finalized=True, notes="too_strict")
        finally:
            service.FINALIZE_MIN_STRICT_SCORE = original
            service.FINALIZE_MIN_ACTIVE_DISHES_FOR_HARD_GATE = original_min_active

    def test_set_override_rejects_invalid_molcajete_forced_dish(self) -> None:
        _insert_dish(34, "Molcajete Invalido", "fuerte", "none", tags=["monday_molcajete"])

        with self.assertRaisesRegex(ValueError, "molcajete"):
            service.set_override(
                "2026-03-02",
                "molcajete",
                forced_dish_id=34,
                note="invalid protein",
            )

    def test_week_diagnostics_explains_monday_molcajete(self) -> None:
        service.generate_week("2026-03-02")
        diagnostics = service.get_week_diagnostics("2026-03-02")

        monday = next(day for day in diagnostics["days"] if day["date"] == "2026-03-02")
        molcajete = next(slot for slot in monday["slots"] if slot["slot"] == "molcajete")

        self.assertTrue(any("obligatorio" in reason.lower() for reason in molcajete["why"]))

    def test_finalize_week_blocks_when_special_slot_loses_required_tag(self) -> None:
        service.generate_week("2026-03-02")

        with db.get_conn() as conn:
            enchiladas_row = conn.execute(
                """
                SELECT dish_id
                FROM menu_item
                WHERE menu_date='2026-03-07' AND slot='enchiladas'
                """
            ).fetchone()
            conn.execute(
                "DELETE FROM dish_tag WHERE dish_id=? AND tag='sat_enchiladas'",
                (int(enchiladas_row["dish_id"]),),
            )
            conn.commit()

        with self.assertRaisesRegex(RuntimeError, "No se puede finalizar la semana"):
            service.finalize_week("2026-03-02", finalized=True, notes="bad_special_tag")

    def test_only_sat_dishes_are_blocked_outside_saturday_even_in_shared_slots(self) -> None:
        _insert_dish(30, "Hamburguesa Tradicional Premium", "fuerte", "res", tags=["only_sat"])

        with db.get_conn() as conn:
            monday_candidates = generator.candidates(conn, "fuerte_res", generator.parse_yyyy_mm_dd("2026-03-02"))
            saturday_candidates = generator.candidates(conn, "fuerte_res", generator.parse_yyyy_mm_dd("2026-03-07"))

        monday_ids = {int(row["id"]) for row in monday_candidates}
        saturday_ids = {int(row["id"]) for row in saturday_candidates}

        self.assertNotIn(30, monday_ids)
        self.assertIn(30, saturday_ids)

    def test_molcajete_candidates_exclude_none_protein(self) -> None:
        _insert_dish(33, "Molcajete Sin Proteina", "fuerte", "none", tags=["monday_molcajete"])

        with db.get_conn() as conn:
            monday_candidates = generator.candidates(conn, "molcajete", generator.parse_yyyy_mm_dd("2026-03-02"))

        monday_ids = {int(row["id"]) for row in monday_candidates}
        self.assertNotIn(33, monday_ids)

    def test_only_fri_dishes_are_blocked_outside_friday_even_in_shared_slots(self) -> None:
        _insert_dish(31, "Mole de Olla Viernes", "fuerte", "res", tags=["only_fri"])

        with db.get_conn() as conn:
            tuesday_candidates = generator.candidates(conn, "fuerte_res", generator.parse_yyyy_mm_dd("2026-03-03"))
            friday_candidates = generator.candidates(conn, "fuerte_res", generator.parse_yyyy_mm_dd("2026-03-06"))

        tuesday_ids = {int(row["id"]) for row in tuesday_candidates}
        friday_ids = {int(row["id"]) for row in friday_candidates}

        self.assertNotIn(31, tuesday_ids)
        self.assertIn(31, friday_ids)

    def test_priority_rule_adds_weight_for_matching_day_and_slot(self) -> None:
        _insert_dish(32, "Res Premium Viernes", "fuerte", "res")
        with db.get_conn() as conn:
            conn.execute(
                """
                INSERT INTO dish_priority_rule(dish_id, weekday, slot, weight, note)
                VALUES (32, 4, 'fuerte_res', 25, 'test')
                """
            )
            conn.commit()
            boosts = generator._priority_boosts_by_dish(
                conn,
                [10, 32],
                generator.parse_yyyy_mm_dd("2026-03-06"),
                "fuerte_res",
            )

        self.assertGreaterEqual(boosts[32], 25)
        self.assertEqual(boosts[10], 0)

    def test_saturday_prefers_only_sat_tagged_dishes_first(self) -> None:
        _insert_dish(40, "Res Especial Sabado", "fuerte", "res", tags=["only_sat"])

        with db.get_conn() as conn:
            pick = generator.pick_with_relaxation(
                conn,
                "fuerte_res",
                generator.parse_yyyy_mm_dd("2026-03-07"),  # sábado
                random.Random("seed-priority-sat"),
            )

        self.assertIsNotNone(pick)
        self.assertEqual(int(pick.dish_id), 40)

    def test_saturday_falls_back_when_only_sat_options_are_not_free(self) -> None:
        _insert_dish(41, "Res Sabado Unica", "fuerte", "res", tags=["only_sat"])

        with db.get_conn() as conn:
            conn.execute(
                """
                INSERT INTO menu_week(week_start_date, generated_at, finalized, notes)
                VALUES ('2026-03-02', '2026-03-02T09:00:00', 0, NULL)
                """
            )
            week_id = int(
                conn.execute(
                    "SELECT id FROM menu_week WHERE week_start_date='2026-03-02'"
                ).fetchone()["id"]
            )
            # El único only_sat ya salió el viernes previo: en sábado queda bloqueado por ventana.
            conn.execute(
                """
                INSERT INTO menu_item(menu_week_id, menu_date, slot, dish_id, is_forced, was_exception, exception_reason, explanation)
                VALUES (?, '2026-03-06', 'fuerte_res', ?, 0, 0, NULL, 'hist')
                """,
                (week_id, 41),
            )
            conn.commit()

            pick = generator.pick_with_relaxation(
                conn,
                "fuerte_res",
                generator.parse_yyyy_mm_dd("2026-03-07"),  # sábado
                random.Random("seed-fallback-sat"),
            )

        self.assertIsNotNone(pick)
        # Debe caer a otra opción libre (catálogo base tiene dish_id=10 para fuerte_res).
        self.assertNotEqual(int(pick.dish_id), 41)

    def test_enchiladas_slot_skips_day_priority_tag(self) -> None:
        sat = generator.parse_yyyy_mm_dd("2026-03-07")
        self.assertIsNone(generator._priority_tag_for_slot_day("enchiladas", sat))
        self.assertEqual(generator._priority_tag_for_slot_day("fuerte_res", sat), "only_sat")

    def test_simulate_generation_quality_runs_in_isolated_copy(self) -> None:
        result = service.simulate_generation_quality("2026-03-02", weeks=2, rerolls_per_week=1)

        self.assertEqual(result["summary"]["total_runs"], 2)
        self.assertEqual(result["summary"]["failed_runs"], 0)
        self.assertEqual(len(result["runs"]), 2)

    def test_regenerate_day_only_recomputes_target_date(self) -> None:
        service.generate_week("2026-03-02")

        with db.get_conn() as conn:
            week_id = int(
                conn.execute(
                    "SELECT id FROM menu_week WHERE week_start_date='2026-03-02'"
                ).fetchone()["id"]
            )
            conn.execute(
                """
                UPDATE menu_item
                SET explanation = 'SENTINEL_TUESDAY'
                WHERE menu_week_id = ?
                  AND menu_date = '2026-03-03'
                  AND slot = 'pasta'
                """,
                (week_id,),
            )
            conn.execute(
                """
                UPDATE menu_item
                SET explanation = 'BROKEN_WEDNESDAY'
                WHERE menu_week_id = ?
                  AND menu_date = '2026-03-04'
                  AND slot = 'pasta'
                """,
                (week_id,),
            )
            conn.commit()

        service.regenerate_day("2026-03-02", "2026-03-04")
        data = service.list_week("2026-03-02")

        tuesday_pasta = next(
            r for r in data["rows"] if r.menu_date == "2026-03-03" and r.slot == "pasta"
        )
        wednesday_pasta = next(
            r for r in data["rows"] if r.menu_date == "2026-03-04" and r.slot == "pasta"
        )

        self.assertEqual(tuesday_pasta.explanation, "SENTINEL_TUESDAY")
        self.assertNotEqual(wednesday_pasta.explanation, "BROKEN_WEDNESDAY")

    def test_strict_audit_warns_when_non_fixed_dish_repeats(self) -> None:
        service.generate_week("2026-03-02")

        with db.get_conn() as conn:
            week_id = int(
                conn.execute(
                    "SELECT id FROM menu_week WHERE week_start_date='2026-03-02'"
                ).fetchone()["id"]
            )
            conn.execute(
                """
                UPDATE menu_item
                SET dish_id = 11
                WHERE menu_week_id = ?
                  AND menu_date = '2026-03-03'
                  AND slot = 'fuerte_pollo'
                """,
                (week_id,),
            )
            conn.execute(
                """
                UPDATE menu_item
                SET dish_id = 11
                WHERE menu_week_id = ?
                  AND menu_date = '2026-03-05'
                  AND slot = 'fuerte_pollo'
                """,
                (week_id,),
            )
            conn.commit()

        audit = service.strict_audit_week("2026-03-02")
        joined = " | ".join(audit.get("warnings", []))
        self.assertIn("Platillo repetido en semana", joined)

    def test_strict_audit_errors_when_sauce_repeats(self) -> None:
        service.generate_week("2026-03-02")

        with db.get_conn() as conn:
            conn.execute("UPDATE dish SET sauce_tag='salsa_test_x' WHERE id IN (10, 11)")
            week_id = int(
                conn.execute(
                    "SELECT id FROM menu_week WHERE week_start_date='2026-03-02'"
                ).fetchone()["id"]
            )
            conn.execute(
                """
                UPDATE menu_item
                SET dish_id = 10
                WHERE menu_week_id = ?
                  AND menu_date = '2026-03-03'
                  AND slot = 'fuerte_res'
                """,
                (week_id,),
            )
            conn.execute(
                """
                UPDATE menu_item
                SET dish_id = 11
                WHERE menu_week_id = ?
                  AND menu_date = '2026-03-04'
                  AND slot = 'fuerte_pollo'
                """,
                (week_id,),
            )
            conn.commit()

        audit = service.strict_audit_week("2026-03-02")
        joined = " | ".join(audit.get("errors", []))
        self.assertIn("Salsa repetida en semana", joined)

    def test_strict_audit_errors_when_beef_cut_repeats_in_weekdays(self) -> None:
        service.generate_week("2026-03-02")

        with db.get_conn() as conn:
            week_id = int(
                conn.execute(
                    "SELECT id FROM menu_week WHERE week_start_date='2026-03-02'"
                ).fetchone()["id"]
            )
            conn.execute("INSERT INTO beef_cut(name) VALUES ('diezmillo_test')")
            cut_id = int(conn.execute("SELECT id FROM beef_cut WHERE name='diezmillo_test'").fetchone()["id"])
            conn.execute("INSERT INTO dish_beef_cut(dish_id, beef_cut_id) VALUES (10, ?)", (cut_id,))
            conn.execute("INSERT INTO dish_beef_cut(dish_id, beef_cut_id) VALUES (15, ?)", (cut_id,))
            conn.execute(
                """
                UPDATE menu_item
                SET dish_id = 10
                WHERE menu_week_id = ?
                  AND menu_date = '2026-03-04'
                  AND slot = 'fuerte_res'
                """,
                (week_id,),
            )
            conn.execute(
                """
                UPDATE menu_item
                SET dish_id = 15
                WHERE menu_week_id = ?
                  AND menu_date = '2026-03-02'
                  AND slot = 'molcajete'
                """,
                (week_id,),
            )
            conn.commit()

        audit = service.strict_audit_week("2026-03-02")
        joined = " | ".join(audit.get("errors", []))
        self.assertIn("Corte de res repetido en L-V", joined)

    def test_strict_audit_errors_when_molcajete_has_none_protein(self) -> None:
        service.generate_week("2026-03-02")
        _insert_dish(35, "Molcajete Sin Proteina Audit", "fuerte", "none", tags=["monday_molcajete"])

        with db.get_conn() as conn:
            week_id = int(
                conn.execute(
                    "SELECT id FROM menu_week WHERE week_start_date='2026-03-02'"
                ).fetchone()["id"]
            )
            conn.execute(
                """
                UPDATE menu_item
                SET dish_id = 35
                WHERE menu_week_id = ?
                  AND menu_date = '2026-03-02'
                  AND slot = 'molcajete'
                """,
                (week_id,),
            )
            conn.commit()

        audit = service.strict_audit_week("2026-03-02")
        joined = " | ".join(audit.get("errors", []))
        self.assertIn("molcajete sin protein definida", joined)

    def test_strict_audit_ignores_expected_salad_mirror_repeat(self) -> None:
        service.generate_week("2026-03-02")

        with db.get_conn() as conn:
            week_id = int(
                conn.execute(
                    "SELECT id FROM menu_week WHERE week_start_date='2026-03-02'"
                ).fetchone()["id"]
            )
            conn.execute(
                """
                UPDATE menu_item
                SET dish_id = 6
                WHERE menu_week_id = ?
                  AND slot = 'ensalada_A'
                  AND menu_date IN ('2026-03-02', '2026-03-05')
                """,
                (week_id,),
            )
            conn.commit()

        audit = service.strict_audit_week("2026-03-02")
        joined = " | ".join(audit.get("warnings", []))
        self.assertNotIn("dish_id=6", joined)

    def test_pick_blocks_same_week_dish_id_before_relaxing(self) -> None:
        _insert_dish(60, "Enchiladas Rojas", "fuerte", tags=["sat_enchiladas"])

        with db.get_conn() as conn:
            conn.execute(
                """
                INSERT INTO menu_week(week_start_date, generated_at, finalized, notes)
                VALUES ('2026-03-02', '2026-03-02T09:00:00', 0, NULL)
                """
            )
            week_id = int(
                conn.execute(
                    "SELECT id FROM menu_week WHERE week_start_date='2026-03-02'"
                ).fetchone()["id"]
            )
            conn.execute(
                """
                INSERT INTO menu_item(menu_week_id, menu_date, slot, dish_id, is_forced, was_exception, exception_reason, explanation)
                VALUES (?, '2026-03-04', 'complemento', 17, 0, 0, NULL, 'hist')
                """,
                (week_id,),
            )
            conn.commit()

            blocked_week_ids = generator.week_non_fixed_dish_ids_used(conn, week_id)
            pick = generator.pick_with_relaxation(
                conn,
                "enchiladas",
                generator.parse_yyyy_mm_dd("2026-03-07"),
                random.Random("seed-week-repeat-block"),
                blocked_dish_ids=blocked_week_ids,
            )

        self.assertIsNotNone(pick)
        self.assertEqual(int(pick.dish_id), 60)


if __name__ == "__main__":
    unittest.main()
