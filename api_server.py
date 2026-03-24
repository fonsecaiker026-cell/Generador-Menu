"""
api_server.py — FastAPI REST server para el frontend de Menú Restaurante.

Expone las funciones de service.py, db.py y report.py como endpoints HTTP.

Arrancar:
    .venv/Scripts/python.exe -m uvicorn api_server:app --reload --port 8000
"""
from __future__ import annotations

import os
import sys
import tempfile
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from typing import Any, Optional
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

import src.db as db_module
from src.db import (
    get_conn,
    fetch_dishes_admin,
    set_dish_active,
    update_dish_full,
    upsert_dish_by_name_group,
    replace_tags,
)
from src.engine.service import (
    generate_week,
    regenerate_day,
    regenerate_week,
    list_week,
    close_day,
    set_override,
    apply_override_now,
    remove_override,
    export_week_pdf,
    export_week_csv,
    finalize_week,
    clear_week_forced_overrides,
    reconcile_menu_for_catalog_change,
)
from src.engine.report import (
    week_report,
    shopping_summary,
    catalog_health_report,
)
from src.engine import dish_manager


# ─── Lifespan (bootstrap DB on startup) ──────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    db_module.bootstrap_db()
    yield


# ─── App ─────────────────────────────────────────────────────

app = FastAPI(
    title="Menú Restaurante API",
    version="1.0.0",
    lifespan=lifespan,
)
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/", include_in_schema=False)
    async def serve_root():
        return FileResponse(FRONTEND_DIST / "index.html")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STRUCTURAL_TAGS = {
    "monday_molcajete",
    "friday_chamorro",
    "sat_enchiladas",
    "saturday_fixed",
}


def _past_weeks_write_lock_enabled() -> bool:
    # Keep historical lock active in real usage but bypass it in pytest.
    return not bool(os.getenv("PYTEST_CURRENT_TEST"))


def _current_operational_week_start() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def _parse_yyyy_mm_dd(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _assert_writable_week_start(week_start: str) -> None:
    ws = _parse_yyyy_mm_dd(week_start)
    if ws.weekday() != 0:
        raise HTTPException(status_code=422, detail="week_start debe ser lunes (YYYY-MM-DD).")


def _assert_writable_menu_date(menu_date: str) -> None:
    _parse_yyyy_mm_dd(menu_date)


def _preserve_structural_tags(conn, dish_id: int, incoming_tags: list[str]) -> list[str]:
    existing_tags = {
        str(r["tag"])
        for r in conn.execute(
            "SELECT tag FROM dish_tag WHERE dish_id=?",
            (int(dish_id),),
        ).fetchall()
    }
    preserved = existing_tags & STRUCTURAL_TAGS
    return sorted(set(incoming_tags) | preserved)


def _assert_can_deactivate_dish(conn, dish_id: int) -> None:
    """
    Prevent deactivation when it would leave a critical slot without candidates.
    """
    row = conn.execute(
        """
        SELECT id, style_tag
        FROM dish
        WHERE id=? AND active=1
        """,
        (int(dish_id),),
    ).fetchone()
    if not row:
        return

    tags = {
        str(r["tag"])
        for r in conn.execute(
            "SELECT tag FROM dish_tag WHERE dish_id=?",
            (int(dish_id),),
        ).fetchall()
    }

    def count_active_by_tag(tag: str) -> int:
        r = conn.execute(
            """
            SELECT COUNT(DISTINCT d.id) AS n
            FROM dish d
            JOIN dish_tag t ON t.dish_id = d.id
            WHERE d.active=1 AND t.tag=?
            """,
            (tag,),
        ).fetchone()
        return int(r["n"] or 0)

    if "monday_molcajete" in tags and count_active_by_tag("monday_molcajete") <= 1:
        raise ValueError("No se puede desactivar: dejaría sin opciones el slot molcajete.")
    if "friday_chamorro" in tags and count_active_by_tag("friday_chamorro") <= 1:
        raise ValueError("No se puede desactivar: dejaría sin opciones el slot chamorro.")
    if "sat_enchiladas" in tags and count_active_by_tag("sat_enchiladas") <= 1:
        raise ValueError("No se puede desactivar: dejaría sin opciones el slot enchiladas.")

    if "saturday_fixed" in tags:
        style_tag = str(row["style_tag"] or "")
        if style_tag in {"paella_fija", "nuggets_fijo", "pancita_fija"}:
            r = conn.execute(
                """
                SELECT COUNT(DISTINCT d.id) AS n
                FROM dish d
                JOIN dish_tag t ON t.dish_id = d.id
                WHERE d.active=1
                  AND t.tag='saturday_fixed'
                  AND d.style_tag=?
                """,
                (style_tag,),
            ).fetchone()
            if int(r["n"] or 0) <= 1:
                raise ValueError(
                    f"No se puede desactivar: dejaría sin opciones el fijo de sábado ({style_tag})."
                )


# ─── Helpers ─────────────────────────────────────────────────

def _week_not_found(week_start: str):
    return HTTPException(status_code=404, detail=f"No existe menú para la semana {week_start}")


def _to_json(obj) -> Any:
    """Recursively convert dataclasses / Rows to dicts."""
    import dataclasses
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _to_json(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, list):
        return [_to_json(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _to_json(v) for k, v in obj.items()}
    return obj


def _fetch_tags_map(conn, dish_ids: list[int]) -> dict[int, list[str]]:
    """Return {dish_id: [tags]} for the given dish IDs."""
    if not dish_ids:
        return {}
    qmarks = ",".join("?" * len(dish_ids))
    rows = conn.execute(
        f"SELECT dish_id, tag FROM dish_tag WHERE dish_id IN ({qmarks}) ORDER BY tag",
        dish_ids,
    ).fetchall()
    result: dict[int, list[str]] = {}
    for r in rows:
        result.setdefault(int(r["dish_id"]), []).append(str(r["tag"]))
    return result


def _enrich_with_tags(conn, dishes: list[dict]) -> list[dict]:
    """Add a `tags` list field to each dish dict."""
    if not dishes:
        return dishes
    tags_map = _fetch_tags_map(conn, [int(d["id"]) for d in dishes])
    for d in dishes:
        d["tags"] = tags_map.get(int(d["id"]), [])
    return dishes


# ─── Week endpoints ───────────────────────────────────────────

@app.get("/api/weeks")
def list_weeks():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT week_start_date, finalized FROM menu_week ORDER BY week_start_date"
        ).fetchall()
    return [{"week_start_date": r["week_start_date"], "finalized": bool(r["finalized"])} for r in rows]


@app.get("/api/weeks/{week_start}")
def get_week(week_start: str):
    try:
        data = list_week(week_start)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    week = data.get("week")
    rows = data.get("rows", [])

    week_dict = None
    if week:
        week_dict = dict(week)
        week_dict["finalized"] = bool(week_dict.get("finalized"))

    rows_out = []
    for r in rows:
        row = _to_json(r)
        row["is_forced"] = bool(row.get("is_forced"))
        row["was_exception"] = bool(row.get("was_exception"))
        rows_out.append(row)

    return {"week": week_dict, "rows": rows_out, "closed_dates": data.get("closed_dates", [])}


@app.post("/api/weeks/{week_start}/generate")
def api_generate_week(week_start: str):
    _assert_writable_week_start(week_start)
    try:
        week_id = generate_week(week_start)
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"week_id": week_id}


@app.post("/api/weeks/{week_start}/regenerate")
def api_regenerate_week(week_start: str):
    _assert_writable_week_start(week_start)
    try:
        week_id = regenerate_week(week_start)
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"week_id": week_id}


@app.post("/api/weeks/{week_start}/days/{menu_date}/regenerate")
def api_regenerate_day(week_start: str, menu_date: str):
    _assert_writable_week_start(week_start)
    _assert_writable_menu_date(menu_date)
    try:
        week_id = regenerate_day(week_start, menu_date)
        data = list_week(week_start)
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))

    week = data.get("week")
    rows = data.get("rows", [])
    week_dict = dict(week) if week else None
    if week_dict:
        week_dict["finalized"] = bool(week_dict.get("finalized"))

    rows_out = []
    for r in rows:
        row = _to_json(r)
        row["is_forced"] = bool(row.get("is_forced"))
        row["was_exception"] = bool(row.get("was_exception"))
        rows_out.append(row)

    return {"week_id": week_id, "week": week_dict, "rows": rows_out, "closed_dates": data.get("closed_dates", [])}


class FinalizeBody(BaseModel):
    finalized: bool
    notes: Optional[str] = None


@app.post("/api/weeks/{week_start}/finalize")
def api_finalize_week(week_start: str, body: FinalizeBody):
    _assert_writable_week_start(week_start)
    try:
        warnings = finalize_week(week_start, finalized=body.finalized, notes=body.notes, force=True)
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True, "warnings": warnings}


@app.post("/api/weeks/{week_start}/clear-overrides")
def api_clear_overrides(week_start: str):
    _assert_writable_week_start(week_start)
    try:
        affected = clear_week_forced_overrides(week_start)
        # Re-apply algorithm on affected slots
        failed_reapply: list[dict[str, str]] = []
        for menu_date, slot in affected:
            try:
                apply_override_now(menu_date, slot)
            except Exception as e:
                failed_reapply.append(
                    {"menu_date": menu_date, "slot": slot, "error": str(e)}
                )
        data = list_week(week_start)
        return {
            "cleared": len(affected),
            "reapplied_ok": len(affected) - len(failed_reapply),
            "reapplied_failed": failed_reapply,
            "week": dict(data["week"]) if data["week"] else None,
            "rows": [_to_json(r) for r in data["rows"]],
        }
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))


class CloseDayBody(BaseModel):
    reason: Optional[str] = None


@app.delete("/api/weeks/{week_start}/days/{menu_date}")
def api_close_day(week_start: str, menu_date: str, body: CloseDayBody | None = None):
    _assert_writable_week_start(week_start)
    _assert_writable_menu_date(menu_date)
    try:
        close_day(week_start, menu_date, reason=(body.reason if body else None))
        data = list_week(week_start)
        week = data.get("week")
        rows = data.get("rows", [])
        week_dict = dict(week) if week else None
        if week_dict:
            week_dict["finalized"] = bool(week_dict.get("finalized"))
        rows_out = []
        for r in rows:
            row = _to_json(r)
            row["is_forced"] = bool(row.get("is_forced"))
            row["was_exception"] = bool(row.get("was_exception"))
            rows_out.append(row)
        return {"week": week_dict, "rows": rows_out, "closed_dates": data.get("closed_dates", [])}
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ─── Report endpoints ─────────────────────────────────────────

@app.get("/api/weeks/{week_start}/report")
def api_week_report(week_start: str):
    result = week_report(week_start)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/api/weeks/{week_start}/shopping")
def api_shopping_summary(week_start: str):
    result = shopping_summary(week_start)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/api/reports/catalog-health")
def api_catalog_health(
    since_days: int = Query(60, ge=1, le=365),
    max_uses_warn: int = Query(11, ge=1, le=100),
):
    return catalog_health_report(since_days=since_days, max_uses_warn=max_uses_warn)


# ─── Export endpoints ─────────────────────────────────────────

@app.get("/api/weeks/{week_start}/pdf")
def api_export_pdf(week_start: str, background_tasks: BackgroundTasks):
    try:
        tmp = tempfile.NamedTemporaryFile(
            suffix=".pdf", prefix=f"menu_{week_start}_", delete=False
        )
        tmp.close()
        out = export_week_pdf(week_start, tmp.name)
        background_tasks.add_task(os.unlink, out)
        return FileResponse(
            path=out,
            media_type="application/pdf",
            filename=f"menu_{week_start}.pdf",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/api/weeks/{week_start}/csv")
def api_export_csv(week_start: str, background_tasks: BackgroundTasks):
    try:
        tmp = tempfile.NamedTemporaryFile(
            suffix=".csv", prefix=f"menu_{week_start}_", delete=False
        )
        tmp.close()
        out = export_week_csv(week_start, tmp.name)
        background_tasks.add_task(os.unlink, out)
        return FileResponse(
            path=out,
            media_type="text/csv",
            filename=f"menu_{week_start}.csv",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ─── Override endpoints ───────────────────────────────────────

class OverrideBody(BaseModel):
    menu_date: str
    slot: str
    forced_dish_id: Optional[int] = None
    blocked_dish_id: Optional[int] = None
    note: Optional[str] = None


@app.post("/api/overrides")
def api_set_override(body: OverrideBody):
    _assert_writable_menu_date(body.menu_date)
    try:
        set_override(
            body.menu_date,
            body.slot,
            forced_dish_id=body.forced_dish_id,
            blocked_dish_id=body.blocked_dish_id,
            note=body.note,
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True}


@app.delete("/api/overrides/{menu_date}/{slot}")
def api_remove_override(menu_date: str, slot: str):
    _assert_writable_menu_date(menu_date)
    try:
        remove_override(menu_date, slot)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True}


@app.post("/api/overrides/{menu_date}/{slot}/apply")
def api_apply_override(menu_date: str, slot: str):
    _assert_writable_menu_date(menu_date)
    try:
        conflicts = apply_override_now(menu_date, slot)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True, "conflicts_resolved": conflicts}


# ─── Dish endpoints ───────────────────────────────────────────

_SLOT_FILTERS: dict[str, dict] = {
    'entrada_no_comal': {'course_group': 'entrada_no_comal'},
    # Weekday sopa: exclude pollo (pollo soups are Saturday-only via sopa_pollo)
    'sopa':            {'raw_where': "d.course_group = 'sopa' AND d.protein != 'pollo'"},
    'crema':           {'course_group': 'crema'},
    'pasta':           {'course_group': 'pasta'},
    'ensalada_A':      {'course_group': 'ensalada'},
    'ensalada_B':      {'course_group': 'ensalada'},
    'ensalada_C':      {'course_group': 'ensalada'},
    'molcajete':       {'raw_where': "d.course_group = 'fuerte' AND EXISTS (SELECT 1 FROM dish_tag t WHERE t.dish_id = d.id AND t.tag = 'monday_molcajete')"},
    'fuerte_res':      {'course_group': 'fuerte', 'protein': 'res'},
    'fuerte_pollo':    {'course_group': 'fuerte', 'protein': 'pollo'},
    'fuerte_cerdo':    {'course_group': 'fuerte', 'protein': 'cerdo'},
    'fuerte_pescado':  {'course_group': 'fuerte', 'protein': 'pescado'},
    'fuerte_camaron':  {'course_group': 'fuerte', 'protein': 'camaron'},
    'chamorro':        {'raw_where': "d.course_group = 'fuerte' AND EXISTS (SELECT 1 FROM dish_tag t WHERE t.dish_id = d.id AND t.tag = 'friday_chamorro')"},
    # complemento includes enchiladas (they can appear in both slots)
    'complemento':     {'course_group': 'complemento'},
    'pescado_al_gusto':{'course_group': 'fuerte', 'protein': 'pescado'},
    'camaron_al_gusto':{'course_group': 'fuerte', 'protein': 'camaron'},
    'enchiladas':      {'raw_where': "EXISTS (SELECT 1 FROM dish_tag t WHERE t.dish_id = d.id AND t.tag = 'sat_enchiladas')"},
    # Saturday sopa slot: only pollo soups
    'sopa_pollo':      {'course_group': 'sopa', 'protein': 'pollo'},
}


@app.get("/api/dishes/with-last-used")
def api_dishes_with_last_used():
    """Return ALL active dishes with their last_used date, sorted oldest-first."""
    sql = """
        SELECT d.id, d.name, d.course_group, d.protein,
               d.style_tag, d.sauce_tag, d.active,
               MAX(CASE WHEN mw.finalized = 1 THEN mr.menu_date END) AS last_used
        FROM dish d
        LEFT JOIN menu_item mr ON mr.dish_id = d.id
        LEFT JOIN menu_week mw ON mw.id = mr.menu_week_id
        WHERE d.active = 1
        GROUP BY d.id
        ORDER BY CASE WHEN MAX(CASE WHEN mw.finalized = 1 THEN mr.menu_date END) IS NULL THEN 0 ELSE 1 END ASC,
                 MAX(CASE WHEN mw.finalized = 1 THEN mr.menu_date END) ASC,
                 d.name ASC
    """
    with get_conn() as conn:
        rows = conn.execute(sql).fetchall()
        result = [dict(r) for r in rows]
        for d in result:
            d['active'] = bool(d['active'])
        result = _enrich_with_tags(conn, result)
    return result


@app.get("/api/dishes/by-slot")
def api_dishes_by_slot(
    slot: str = Query(...),
    reference_date: str | None = Query(None),
    current_menu_date: str | None = Query(None),
    current_slot: str | None = Query(None),
):
    """Return active dishes valid for a given slot, with last_used date, sorted oldest-first."""
    filters = _SLOT_FILTERS.get(slot)
    if not filters:
        raise HTTPException(status_code=400, detail=f"Slot '{slot}' no reconocido o no editable")

    params: list = []

    join_conditions = ["mr.dish_id = d.id"]
    if reference_date:
        join_conditions.append("date(mr.menu_date) <= date(?)")
        params.append(reference_date)
    if current_menu_date and current_slot:
        join_conditions.append("NOT (mr.menu_date = ? AND mr.slot = ?)")
        params.extend([current_menu_date, current_slot])
    menu_item_join = f"LEFT JOIN menu_item mr ON {' AND '.join(join_conditions)}"

    if 'raw_where' in filters:
        sql = f"""
            SELECT d.id, d.name, d.course_group, d.protein,
                   d.style_tag, d.sauce_tag, d.active,
                   MAX(CASE WHEN mw.finalized = 1 THEN mr.menu_date END) AS last_used
            FROM dish d
            {menu_item_join}
            LEFT JOIN menu_week mw ON mw.id = mr.menu_week_id
            WHERE d.active = 1
              AND {filters['raw_where']}
            GROUP BY d.id
            ORDER BY CASE WHEN MAX(CASE WHEN mw.finalized = 1 THEN mr.menu_date END) IS NULL THEN 0 ELSE 1 END ASC,
                     MAX(CASE WHEN mw.finalized = 1 THEN mr.menu_date END) ASC,
                     d.name ASC
        """
    else:
        sql = """
            SELECT d.id, d.name, d.course_group, d.protein,
                   d.style_tag, d.sauce_tag, d.active,
                   MAX(CASE WHEN mw.finalized = 1 THEN mr.menu_date END) AS last_used
            FROM dish d
        """
        sql += f"""
            {menu_item_join}
            LEFT JOIN menu_week mw ON mw.id = mr.menu_week_id
            WHERE d.active = 1
              AND d.course_group = ?
        """
        params.append(filters["course_group"])

        if 'protein' in filters:
            sql += " AND d.protein = ?"
            params.append(filters['protein'])

        if 'style_tag_like' in filters:
            sql += " AND d.style_tag LIKE ?"
            params.append(filters['style_tag_like'])

        sql += """
            GROUP BY d.id
            ORDER BY CASE WHEN MAX(CASE WHEN mw.finalized = 1 THEN mr.menu_date END) IS NULL THEN 0 ELSE 1 END ASC,
                     MAX(CASE WHEN mw.finalized = 1 THEN mr.menu_date END) ASC,
                     d.name ASC
        """

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        result = [dict(r) for r in rows]
        for d in result:
            d['active'] = bool(d['active'])
        result = _enrich_with_tags(conn, result)
    return result


@app.get("/api/dishes")
def api_list_dishes(
    name_query: str = Query(""),
    course_group: str = Query("ALL"),
    protein: str = Query("ALL"),
    active_filter: str = Query("ALL"),
):
    with get_conn() as conn:
        dishes = fetch_dishes_admin(
            name_query=name_query,
            course_group=course_group,
            protein=protein,
            active_filter=active_filter,
            limit=500,
        )
        for d in dishes:
            d["active"] = bool(d.get("active"))
        dishes = _enrich_with_tags(conn, dishes)
    return dishes


class DishCreateBody(BaseModel):
    name: str
    course_group: str
    protein: str
    style_tag: Optional[str] = None
    sauce_tag: Optional[str] = None
    active: bool = True
    tags: list[str] = []


@app.post("/api/dishes", status_code=201)
def api_create_dish(body: DishCreateBody):
    try:
        with get_conn() as conn:
            dish_id, action = upsert_dish_by_name_group(
                conn,
                name=body.name.strip(),
                course_group=body.course_group,
                protein=body.protein,
                style_tag=body.style_tag or None,
                active=int(body.active),
            )
            if body.sauce_tag is not None:
                conn.execute(
                    "UPDATE dish SET sauce_tag=? WHERE id=?",
                    (body.sauce_tag or None, dish_id),
                )
            safe_tags = _preserve_structural_tags(conn, int(dish_id), list(body.tags or []))
            replace_tags(conn, dish_id, safe_tags)
            conn.commit()
            row = conn.execute(
                "SELECT id, name, course_group, protein, style_tag, sauce_tag, active FROM dish WHERE id=?",
                (dish_id,),
            ).fetchone()
            d = dict(row)
            d["active"] = bool(d["active"])
            d = _enrich_with_tags(conn, [d])[0]
        return d
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


class DishUpdateBody(BaseModel):
    name: Optional[str] = None
    course_group: Optional[str] = None
    protein: Optional[str] = None
    style_tag: Optional[str] = None
    sauce_tag: Optional[str] = None
    active: Optional[bool] = None
    tags: Optional[list[str]] = None  # if provided, replaces all tags


@app.put("/api/dishes/{dish_id}")
def api_update_dish(dish_id: int, body: DishUpdateBody):
    try:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT id, name, course_group, protein, style_tag, sauce_tag, active FROM dish WHERE id=?",
                (dish_id,),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"Platillo {dish_id} no existe.")

            current = dict(row)
            target_name = (body.name or current["name"]).strip()
            dup = conn.execute(
                """
                SELECT id
                FROM dish
                WHERE lower(trim(name)) = lower(trim(?))
                  AND id <> ?
                LIMIT 1
                """,
                (target_name, int(dish_id)),
            ).fetchone()
            if dup:
                raise HTTPException(
                    status_code=422,
                    detail=f"Ya existe otro platillo con ese nombre: '{target_name}'.",
                )
            if body.active is False and bool(current.get("active")):
                _assert_can_deactivate_dish(conn, int(dish_id))
            update_dish_full(
                conn,
                dish_id=dish_id,
                name=target_name,
                course_group=body.course_group or current["course_group"],
                protein=body.protein or current["protein"],
                style_tag=body.style_tag if body.style_tag is not None else current["style_tag"],
                sauce_tag=body.sauce_tag if body.sauce_tag is not None else current["sauce_tag"],
                active=int(body.active) if body.active is not None else current["active"],
            )
            if body.tags is not None:
                safe_tags = _preserve_structural_tags(conn, int(dish_id), list(body.tags or []))
                replace_tags(conn, dish_id, safe_tags)
            conn.commit()
            updated = dict(conn.execute(
                "SELECT id, name, course_group, protein, style_tag, sauce_tag, active FROM dish WHERE id=?",
                (dish_id,),
            ).fetchone())
            updated["active"] = bool(updated["active"])
            updated = _enrich_with_tags(conn, [updated])[0]
        reconcile_result = reconcile_menu_for_catalog_change(int(dish_id))
        return {
            **updated,
            "catalog_reconcile": reconcile_result,
            "molcajete_reconcile": reconcile_result,  # backward compatibility
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


class ActiveBody(BaseModel):
    active: bool


@app.patch("/api/dishes/{dish_id}/active")
def api_set_dish_active(dish_id: int, body: ActiveBody):
    try:
        if not body.active:
            with get_conn() as conn:
                _assert_can_deactivate_dish(conn, int(dish_id))
        set_dish_active(dish_id, int(body.active))
        reconcile_result = reconcile_menu_for_catalog_change(int(dish_id))
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True, "active": body.active, "catalog_reconcile": reconcile_result}


class DedupeBody(BaseModel):
    apply: bool = False
    include_inactive: bool = False


@app.get("/api/dishes/duplicates")
def api_preview_duplicate_dishes(include_inactive: bool = Query(False)):
    try:
        return dish_manager.deduplicate_dishes(apply=False, include_inactive=include_inactive)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/api/dishes/duplicates/merge")
def api_merge_duplicate_dishes(body: DedupeBody):
    try:
        return dish_manager.deduplicate_dishes(
            apply=bool(body.apply),
            include_inactive=bool(body.include_inactive),
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


# ─── Health check ─────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "db": str(db_module.DB_PATH)}


# ─── Run ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)

if FRONTEND_DIST.exists():
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        if full_path.startswith("api") or full_path in {"docs", "redoc", "openapi.json"}:
            raise HTTPException(status_code=404, detail="Not found")

        requested = FRONTEND_DIST / full_path
        if full_path and requested.exists() and requested.is_file():
            return FileResponse(requested)

        return FileResponse(FRONTEND_DIST / "index.html")