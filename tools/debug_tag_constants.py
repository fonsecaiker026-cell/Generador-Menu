import os, sys, re, inspect
sys.path.insert(0, os.path.abspath("."))

from datetime import date
from src.db import get_conn
import src.engine.generator as g

print("generator_file =", g.__file__)
src = inspect.getsource(g.candidates)

# imprime un pedazo grande alrededor de "slot == \"chamorro\""
m = re.search(r"elif\s+slot\s*==\s*['\"]chamorro['\"]:(.*?)(elif|else:)", src, re.S)
if not m:
    print("❌ No encontré el bloque chamorro en candidates()")
else:
    print("\n=== BLOQUE CHAMORRO EN candidates() ===\n")
    print(m.group(0))

# ahora corre candidates y además ejecuta un SQL simple directo para comparar
with get_conn() as c:
    day = date(2026, 1, 30)
    cand = g.candidates(c, "chamorro", day)
    print("\n=== RESULTADO candidates(chamorro) ===")
    print("count =", len(cand))
    print("sample =", cand[:5])

    rows = c.execute("""
        SELECT d.id, d.name, d.course_group, d.protein, d.active
        FROM dish d
        JOIN dish_tag t ON t.dish_id=d.id
        WHERE d.active=1 AND d.course_group='fuerte' AND t.tag='friday_chamorro'
        ORDER BY d.id
    """).fetchall()
    print("\n=== SQL DIRECTO (fuerte + friday_chamorro) ===")
    for r in rows:
        print(r["id"], "|", r["name"], "|", r["course_group"], "|", r["protein"], "|", r["active"])

