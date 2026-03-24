from __future__ import annotations

from datetime import date, timedelta
from typing import Any
import re
import unicodedata

from src.db import get_conn

VALID_COURSE_GROUPS = {
    "entrada_no_comal",
    "sopa",
    "crema",
    "pasta",
    "arroz",
    "ensalada",
    "fuerte",
    "complemento",
    "especial",
}

VALID_PROTEINS = {
    "none",
    "res",
    "pollo",
    "cerdo",
    "pescado",
    "camaron",
}

PROTEIN_ALIASES = {
    "atun": "pescado",
    "marisco": "pescado",
}

ALLOWED_UPDATE_FIELDS = {
    "name",
    "course_group",
    "protein",
    "style_tag",
    "sauce_tag",
    "active",
    "tags",
}

TAG_MONDAY_MOLCAJETE = "monday_molcajete"


def _ensure_sauce_tag_column(conn) -> None:
    """Ensure `dish.sauce_tag` exists before any read/write that depends on it."""
    cols = conn.execute("PRAGMA table_info(dish)").fetchall()
    if any(str(r["name"]) == "sauce_tag" for r in cols):
        return

    try:
        conn.execute("ALTER TABLE dish ADD COLUMN sauce_tag TEXT")
    except Exception:
        cols = conn.execute("PRAGMA table_info(dish)").fetchall()
        if not any(str(r["name"]) == "sauce_tag" for r in cols):
            raise


def _normalize_text(value: Any, *, field: str, allow_none: bool = False) -> str | None:
    if value is None:
        if allow_none:
            return None
        raise ValueError(f"'{field}' es obligatorio.")

    text = str(value).strip()
    if not text:
        if allow_none:
            return None
        raise ValueError(f"'{field}' no puede estar vacío.")
    return text


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_tags(tags: list[str] | tuple[str, ...] | set[str] | None) -> list[str]:
    if tags is None:
        return []
    if not isinstance(tags, (list, tuple, set)):
        raise ValueError("'tags' debe ser una lista/tuple/set de strings.")

    seen: set[str] = set()
    out: list[str] = []
    for raw in tags:
        tag = _normalize_text(raw, field="tag")
        if tag in seen:
            continue
        seen.add(tag)
        out.append(tag)
    return out


def _validate_course_group(course_group: str) -> str:
    value = _normalize_text(course_group, field="course_group")
    if value not in VALID_COURSE_GROUPS:
        raise ValueError(f"course_group inválido: {value}")
    return value


def _validate_protein(protein: str) -> str:
    value = _normalize_text(protein, field="protein")
    value = PROTEIN_ALIASES.get(value, value)
    if value not in VALID_PROTEINS:
        raise ValueError(f"protein inválida: {value}")
    return value


def _validate_name(name: str) -> str:
    value = _normalize_text(name, field="name")
    if len(value) < 3:
        raise ValueError("El nombre debe tener al menos 3 caracteres.")
    if len(value) > 120:
        raise ValueError("El nombre no puede exceder 120 caracteres.")
    return value


def _validate_active(active: Any) -> int:
    if isinstance(active, bool):
        return int(active)
    if active in (0, 1):
        return int(active)
    raise ValueError("'active' debe ser 0/1 o bool.")


def _fetch_dish_row(conn, dish_id: int):
    row = conn.execute("SELECT * FROM dish WHERE id=?", (int(dish_id),)).fetchone()
    if not row:
        raise ValueError(f"No existe dish_id={dish_id}.")
    return row


def _assert_unique_name(conn, name: str, *, exclude_id: int | None = None) -> None:
    q = "SELECT id FROM dish WHERE lower(trim(name))=lower(trim(?))"
    params: list[Any] = [name]
    if exclude_id is not None:
        q += " AND id != ?"
        params.append(int(exclude_id))
    row = conn.execute(q, tuple(params)).fetchone()
    if row:
        raise ValueError(f"Ya existe otro platillo con nombre '{name}'.")


def _replace_tags(conn, dish_id: int, tags: list[str]) -> None:
    conn.execute("DELETE FROM dish_tag WHERE dish_id=?", (int(dish_id),))
    if tags:
        conn.executemany(
            "INSERT INTO dish_tag(dish_id, tag) VALUES (?, ?)",
            [(int(dish_id), tag) for tag in tags],
        )


def _validate_special_tag_constraints(*, protein: str, tags: list[str]) -> None:
    if TAG_MONDAY_MOLCAJETE in tags and protein == "none":
        raise ValueError(
            "Platillos con tag 'monday_molcajete' deben tener protein distinta de 'none'."
        )


def _canonical_name(name: str) -> str:
    """
    Normalized key for duplicate detection:
    - lowercased
    - accents removed
    - punctuation collapsed to spaces
    """
    txt = (name or "").strip().lower()
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(ch for ch in txt if not unicodedata.combining(ch))
    txt = re.sub(r"[^a-z0-9]+", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def create_dish(
    name: str,
    course_group: str,
    protein: str,
    style_tag: str | None,
    sauce_tag: str | None,
    tags: list[str] | tuple[str, ...] | set[str] | None,
) -> int:
    """Create a dish with validated fields and replaceable tag metadata."""
    clean_name = _validate_name(name)
    clean_course_group = _validate_course_group(course_group)
    clean_protein = _validate_protein(protein)
    clean_style_tag = _normalize_optional_text(style_tag)
    clean_sauce_tag = _normalize_optional_text(sauce_tag)
    clean_tags = _normalize_tags(tags)
    _validate_special_tag_constraints(protein=clean_protein, tags=clean_tags)

    with get_conn() as conn:
        _ensure_sauce_tag_column(conn)
        _assert_unique_name(conn, clean_name)

        cur = conn.execute(
            """
            INSERT INTO dish(name, course_group, protein, style_tag, sauce_tag, active)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (
                clean_name,
                clean_course_group,
                clean_protein,
                clean_style_tag,
                clean_sauce_tag,
            ),
        )
        dish_id = int(cur.lastrowid)
        _replace_tags(conn, dish_id, clean_tags)
        conn.commit()
        return dish_id


def update_dish(dish_id: int, **fields) -> dict[str, Any]:
    """Update one or more dish fields, revalidating the full resulting record."""
    if not fields:
        raise ValueError("Debes enviar al menos un campo para actualizar.")

    invalid = sorted(set(fields) - ALLOWED_UPDATE_FIELDS)
    if invalid:
        raise ValueError(f"Campos no permitidos: {', '.join(invalid)}")

    with get_conn() as conn:
        _ensure_sauce_tag_column(conn)
        current = dict(_fetch_dish_row(conn, int(dish_id)))

        merged = {
            "name": current["name"],
            "course_group": current["course_group"],
            "protein": current["protein"],
            "style_tag": current["style_tag"],
            "sauce_tag": current.get("sauce_tag"),
            "active": current["active"],
            "tags": [r["tag"] for r in conn.execute("SELECT tag FROM dish_tag WHERE dish_id=? ORDER BY tag", (int(dish_id),)).fetchall()],
        }
        merged.update(fields)

        clean_name = _validate_name(merged["name"])
        clean_course_group = _validate_course_group(merged["course_group"])
        clean_protein = _validate_protein(merged["protein"])
        clean_style_tag = _normalize_optional_text(merged.get("style_tag"))
        clean_sauce_tag = _normalize_optional_text(merged.get("sauce_tag"))
        clean_active = _validate_active(merged["active"])
        clean_tags = _normalize_tags(merged.get("tags"))
        _validate_special_tag_constraints(protein=clean_protein, tags=clean_tags)

        _assert_unique_name(conn, clean_name, exclude_id=int(dish_id))

        conn.execute(
            """
            UPDATE dish
            SET name=?,
                course_group=?,
                protein=?,
                style_tag=?,
                sauce_tag=?,
                active=?
            WHERE id=?
            """,
            (
                clean_name,
                clean_course_group,
                clean_protein,
                clean_style_tag,
                clean_sauce_tag,
                clean_active,
                int(dish_id),
            ),
        )
        if "tags" in fields:
            _replace_tags(conn, int(dish_id), clean_tags)

        conn.commit()
        return dish_detail(int(dish_id))


def deactivate_dish(dish_id: int) -> None:
    """Soft-delete a dish if it has no active future overrides referencing it."""
    today = date.today().isoformat()
    with get_conn() as conn:
        _ensure_sauce_tag_column(conn)
        _fetch_dish_row(conn, int(dish_id))

        conflicts = conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM menu_override
            WHERE date(menu_date) >= date(?)
              AND (forced_dish_id=? OR blocked_dish_id=?)
            """,
            (today, int(dish_id), int(dish_id)),
        ).fetchone()

        if int(conflicts["n"] or 0) > 0:
            raise ValueError("No se puede desactivar: tiene overrides futuros activos.")

        conn.execute("UPDATE dish SET active=0 WHERE id=?", (int(dish_id),))
        conn.commit()


def merge_dishes(keep_id: int, delete_id: int) -> None:
    """Merge duplicate dishes by reassigning references, then deleting the redundant row."""
    keep_id = int(keep_id)
    delete_id = int(delete_id)
    if keep_id == delete_id:
        raise ValueError("keep_id y delete_id deben ser distintos.")

    with get_conn() as conn:
        _ensure_sauce_tag_column(conn)
        keep = dict(_fetch_dish_row(conn, keep_id))
        _fetch_dish_row(conn, delete_id)

        menu_duplicates = conn.execute(
            """
            SELECT d.id
            FROM menu_item d
            JOIN menu_item k
              ON k.menu_date = d.menu_date
             AND k.slot = d.slot
             AND k.dish_id = ?
            WHERE d.dish_id = ?
            """,
            (keep_id, delete_id),
        ).fetchall()
        if menu_duplicates:
            conn.executemany("DELETE FROM menu_item WHERE id=?", [(int(r["id"]),) for r in menu_duplicates])
        conn.execute("UPDATE menu_item SET dish_id=? WHERE dish_id=?", (keep_id, delete_id))

        conn.execute(
            """
            INSERT OR IGNORE INTO dish_tag(dish_id, tag)
            SELECT ?, tag
            FROM dish_tag
            WHERE dish_id=?
            """,
            (keep_id, delete_id),
        )
        conn.execute("DELETE FROM dish_tag WHERE dish_id=?", (delete_id,))

        conn.execute(
            """
            INSERT OR IGNORE INTO dish_beef_cut(dish_id, beef_cut_id)
            SELECT ?, beef_cut_id
            FROM dish_beef_cut
            WHERE dish_id=?
            """,
            (keep_id, delete_id),
        )
        conn.execute("DELETE FROM dish_beef_cut WHERE dish_id=?", (delete_id,))

        keep_season = conn.execute("SELECT 1 FROM dish_season WHERE dish_id=?", (keep_id,)).fetchone()
        if not keep_season:
            conn.execute(
                """
                INSERT OR REPLACE INTO dish_season(dish_id, rule, start_month, end_month)
                SELECT ?, rule, start_month, end_month
                FROM dish_season
                WHERE dish_id=?
                """,
                (keep_id, delete_id),
            )
        conn.execute("DELETE FROM dish_season WHERE dish_id=?", (delete_id,))

        conn.execute("UPDATE dish_lock SET dish_id=? WHERE dish_id=?", (keep_id, delete_id))

        conn.execute(
            "UPDATE menu_override SET forced_dish_id=? WHERE forced_dish_id=?",
            (keep_id, delete_id),
        )
        conn.execute(
            "UPDATE menu_override SET blocked_dish_id=? WHERE blocked_dish_id=?",
            (keep_id, delete_id),
        )

        if not keep.get("sauce_tag"):
            conn.execute(
                """
                UPDATE dish
                SET sauce_tag = COALESCE(sauce_tag, (SELECT sauce_tag FROM dish WHERE id=?))
                WHERE id=?
                """,
                (delete_id, keep_id),
            )

        conn.execute("DELETE FROM dish WHERE id=?", (delete_id,))
        conn.commit()


def find_duplicate_groups(*, include_inactive: bool = False) -> list[dict[str, Any]]:
    """
    Detect likely duplicate dishes by canonicalized name, course_group and protein.
    Groups are conservative to avoid merging genuinely different dishes.
    """
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, name, course_group, protein, active
            FROM dish
            """
        ).fetchall()

    buckets: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        item = dict(row)
        if not include_inactive and int(item["active"] or 0) != 1:
            continue
        key = (
            _canonical_name(str(item["name"])),
            str(item["course_group"]),
            str(item["protein"]),
        )
        buckets.setdefault(key, []).append(item)

    groups: list[dict[str, Any]] = []
    for (canonical, course_group, protein), items in buckets.items():
        if len(items) <= 1:
            continue
        # Keep active first, then oldest id for stable references.
        ordered = sorted(items, key=lambda x: (-int(x["active"] or 0), int(x["id"])))
        keep = ordered[0]
        drops = ordered[1:]
        groups.append(
            {
                "canonical_name": canonical,
                "course_group": course_group,
                "protein": protein,
                "keep_id": int(keep["id"]),
                "keep_name": str(keep["name"]),
                "drop_ids": [int(x["id"]) for x in drops],
                "drop_names": [str(x["name"]) for x in drops],
                "size": len(ordered),
            }
        )

    groups.sort(key=lambda g: (-int(g["size"]), g["canonical_name"]))
    return groups


def deduplicate_dishes(*, apply: bool = False, include_inactive: bool = False) -> dict[str, Any]:
    """
    Preview or execute duplicate merges.
    """
    groups = find_duplicate_groups(include_inactive=include_inactive)
    if not apply:
        return {
            "apply": False,
            "groups": groups,
            "groups_count": len(groups),
            "merge_operations": sum(len(g["drop_ids"]) for g in groups),
        }

    merged: list[dict[str, Any]] = []
    for group in groups:
        keep_id = int(group["keep_id"])
        for drop_id in group["drop_ids"]:
            merge_dishes(keep_id, int(drop_id))
            merged.append(
                {
                    "keep_id": keep_id,
                    "drop_id": int(drop_id),
                    "canonical_name": group["canonical_name"],
                }
            )

    return {
        "apply": True,
        "groups_count": len(groups),
        "merged_count": len(merged),
        "merged": merged,
    }


def bulk_set_sauce_tag(dish_ids: list[int] | tuple[int, ...] | set[int], sauce_tag: str | None) -> int:
    """Set the same sauce tag for multiple dishes in one transaction."""
    if not isinstance(dish_ids, (list, tuple, set)) or not dish_ids:
        raise ValueError("'dish_ids' debe ser una colección no vacía.")

    ids = sorted({int(x) for x in dish_ids})
    clean_sauce_tag = _normalize_optional_text(sauce_tag)

    with get_conn() as conn:
        _ensure_sauce_tag_column(conn)
        qmarks = ",".join("?" for _ in ids)
        found = conn.execute(f"SELECT id FROM dish WHERE id IN ({qmarks})", tuple(ids)).fetchall()
        found_ids = {int(r["id"]) for r in found}
        missing = [str(x) for x in ids if x not in found_ids]
        if missing:
            raise ValueError(f"No existen dish_ids: {', '.join(missing)}")

        cur = conn.execute(
            f"UPDATE dish SET sauce_tag=? WHERE id IN ({qmarks})",
            (clean_sauce_tag, *ids),
        )
        conn.commit()
        return int(cur.rowcount)


def search_dishes(
    query: str | None = None,
    course_group: str | None = None,
    protein: str | None = None,
    sauce_tag: str | None = None,
    active: bool | int | None = None,
) -> list[dict[str, Any]]:
    """Search dishes with optional text, group, protein, sauce and active-state filters."""
    with get_conn() as conn:
        _ensure_sauce_tag_column(conn)

        sql = """
            SELECT
                d.id,
                d.name,
                d.course_group,
                d.protein,
                d.style_tag,
                d.sauce_tag,
                d.active,
                GROUP_CONCAT(dt.tag, '|') AS tags
            FROM dish d
            LEFT JOIN dish_tag dt ON dt.dish_id = d.id
            WHERE 1=1
        """
        params: list[Any] = []

        if query and str(query).strip():
            sql += " AND lower(d.name) LIKE ?"
            params.append(f"%{str(query).strip().lower()}%")

        if course_group is not None:
            sql += " AND d.course_group = ?"
            params.append(_validate_course_group(course_group))

        if protein is not None:
            sql += " AND d.protein = ?"
            params.append(_validate_protein(protein))

        if sauce_tag is not None:
            clean_sauce_tag = _normalize_optional_text(sauce_tag)
            if clean_sauce_tag is None:
                sql += " AND (d.sauce_tag IS NULL OR trim(d.sauce_tag)='')"
            else:
                sql += " AND d.sauce_tag = ?"
                params.append(clean_sauce_tag)

        if active is not None:
            sql += " AND d.active = ?"
            params.append(_validate_active(active))

        sql += """
            GROUP BY d.id, d.name, d.course_group, d.protein, d.style_tag, d.sauce_tag, d.active
            ORDER BY d.active DESC, d.name ASC
        """

        rows = conn.execute(sql, tuple(params)).fetchall()

    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["tags"] = sorted([t for t in (item.get("tags") or "").split("|") if t])
        result.append(item)
    return result


def dish_detail(dish_id: int) -> dict[str, Any]:
    """Return dish data, tags, last-60-day usage history and upcoming overrides."""
    today = date.today()
    start = (today - timedelta(days=60)).isoformat()

    with get_conn() as conn:
        _ensure_sauce_tag_column(conn)
        dish = dict(_fetch_dish_row(conn, int(dish_id)))

        tags = [
            r["tag"]
            for r in conn.execute(
                "SELECT tag FROM dish_tag WHERE dish_id=? ORDER BY tag",
                (int(dish_id),),
            ).fetchall()
        ]

        usage_history = [
            dict(r)
            for r in conn.execute(
                """
                SELECT
                    mi.menu_date,
                    mi.slot,
                    mi.menu_week_id,
                    mi.is_forced,
                    mi.was_exception,
                    mi.exception_reason,
                    mi.explanation
                FROM menu_item mi
                WHERE mi.dish_id=?
                  AND date(mi.menu_date) >= date(?)
                ORDER BY date(mi.menu_date) DESC, mi.slot ASC
                """,
                (int(dish_id), start),
            ).fetchall()
        ]

        upcoming_overrides = [
            dict(r)
            for r in conn.execute(
                """
                SELECT
                    menu_date,
                    slot,
                    forced_dish_id,
                    blocked_dish_id,
                    note,
                    created_at
                FROM menu_override
                WHERE date(menu_date) >= date(?)
                  AND (forced_dish_id=? OR blocked_dish_id=?)
                ORDER BY date(menu_date) ASC, slot ASC
                """,
                (today.isoformat(), int(dish_id), int(dish_id)),
            ).fetchall()
        ]

    return {
        "dish": dish,
        "tags": tags,
        "usage_history_60d": usage_history,
        "upcoming_overrides": upcoming_overrides,
    }
