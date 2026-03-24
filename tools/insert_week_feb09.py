#!/usr/bin/env python3
"""
Paso 2: renames feb 9-14 + creates feb 9-14 + insertar semana 2026-02-09
(feb 2-7 renames/creates ya fueron aplicados en sesión anterior)
"""
import sqlite3, sys
from datetime import date, timedelta

sys.stdout.reconfigure(encoding='utf-8')

DB = 'data/app.db'
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
conn.execute('PRAGMA foreign_keys = ON')

def rename(dish_id: int, new_name: str):
    old = conn.execute('SELECT name FROM dish WHERE id=?', (dish_id,)).fetchone()
    if not old:
        print(f'  WARN: dish {dish_id} not found')
        return
    if old['name'] == new_name:
        print(f'  SKIP (ya ok) [{dish_id}] "{new_name}"')
        return
    # Check unique
    dup = conn.execute('SELECT id FROM dish WHERE name=? AND id!=?', (new_name, dish_id)).fetchone()
    if dup:
        print(f'  WARN: ya existe "{new_name}" como id={dup["id"]}, skip rename {dish_id}')
        return
    conn.execute('UPDATE dish SET name=? WHERE id=?', (new_name, dish_id))
    print(f'  RENAME [{dish_id}] → "{new_name}"')

def get_or_create(name: str, course_group: str, protein: str,
                  style_tag: str = None, tags: list = None) -> int:
    row = conn.execute('SELECT id FROM dish WHERE LOWER(name)=LOWER(?)', (name,)).fetchone()
    if row:
        print(f'  SKIP (existe) [{row["id"]}] "{name}"')
        return row['id']
    c = conn.execute(
        'INSERT INTO dish (name, course_group, protein, style_tag, active) VALUES (?,?,?,?,1)',
        (name, course_group, protein, style_tag)
    )
    dish_id = c.lastrowid
    if tags:
        for tag in tags:
            conn.execute('INSERT OR IGNORE INTO dish_tag (dish_id, tag) VALUES (?,?)',
                         (dish_id, tag))
    print(f'  CREATE [{dish_id}] "{name}" ({course_group}/{protein})')
    return dish_id

# ─────────────────────────────────────────────────────
# 1) RENAMES — semana feb 9-14
# ─────────────────────────────────────────────────────
print('\n=== RENAMES sem feb 9-14 ===')
rename(481,  'Sopa de Champiñones')
rename(1278, 'Ensalada de Betabel con Naranja')
rename(1397, 'Chuleta de Cerdo Ahumada con Ensalada y Papas')
rename(1479, 'Cerdo en Salsa de Chile Morita con Nopales')
rename(1075, 'Tortitas de Espinaca Rellenas de Queso en Salsa Verde')
rename(1545, 'Crema de Chicharrón')
rename(557,  'Fideo Seco con Mole')
rename(1003, 'Tortitas de Pollo en Salsa Verde')
rename(1106, 'Chile Relleno de Queso')
rename(1240, 'Empanadas Argentinas de Espinacas con Queso')
rename(496,  'Crema de Queso con Uvas')
rename(1321, 'Medallones de Cerdo a los Tres Chiles')
rename(739,  'Camarones al Coco con Dip de Mango')
rename(1221, 'Tostada de Ceviche de Pescado')

conn.commit()

# ─────────────────────────────────────────────────────
# 2) CREATE NEW — semana feb 9-14
# ─────────────────────────────────────────────────────
print('\n=== CREATE NEW sem feb 9-14 ===')
id_pasta_almeja        = get_or_create('Sopa de Pasta con Almeja',    'pasta',  'marisco')
id_molcajete_enchilada = get_or_create('Molcajete de Carne Enchilada','fuerte', 'cerdo',
                                        tags=['monday_molcajete'])
id_crema_jalapeno      = get_or_create('Crema de Jalapeño con Queso', 'crema',  'none')
id_espagueti_finas     = get_or_create('Espagueti a las Finas Hierbas','pasta', 'none')
id_huarache_costilla   = get_or_create('Huarache con Costilla de Res','fuerte', 'res')
id_tacos_camaron_guac  = get_or_create('Tacos de Camarón con Guacamole','fuerte','camaron')
id_fusilli_olivo       = get_or_create('Fusilli a las Finas Hierbas con Aceite de Olivo','pasta','none')
id_parrillada_agujas   = get_or_create('Parrillada de Agujas Norteñas','fuerte','res')
id_filete_aceituna     = get_or_create('Filete de Pescado en Salsa de Aceituna Negra','fuerte','pescado')
id_montadito_espinaca  = get_or_create('Montadito de Espinaca con Queso','entrada','none')
id_fetuccini_pesto     = get_or_create('Fetuccini al Pesto',           'pasta',  'none')
id_bistec_res          = get_or_create('Bistec de Res Encebollado',    'fuerte', 'res')
id_cerdo_pipian        = get_or_create('Cerdo en Pipian',              'fuerte', 'cerdo')
id_filete_mantequilla  = get_or_create('Filete de Pescado a la Mantequilla Vaquera','fuerte','pescado')
id_torta_jamon         = get_or_create('Torta de Jamón con Frijoles, Queso, Jitomate, Cebolla y Aguacate',
                                        'complemento','none')
id_filete_cremosa_esp  = get_or_create('Filete de Pescado en Salsa Cremosa de Espinaca','fuerte','pescado')
id_ensalada_paraiso    = get_or_create('Ensalada Paraíso',             'ensalada','none')
id_filete_vino_almejas = get_or_create('Filete de Pescado al Vino Blanco con Almejas','fuerte','pescado')

conn.commit()

# ─────────────────────────────────────────────────────
# 3) IDs fijos
# ─────────────────────────────────────────────────────
ARROZ_ID   = 1596
COMAL_ID   = 202

row_pancita  = conn.execute("SELECT id FROM dish WHERE LOWER(name) LIKE '%pancita%' AND active=1 LIMIT 1").fetchone()
row_paella   = conn.execute("SELECT id FROM dish WHERE LOWER(name) LIKE '%paella%' AND active=1 LIMIT 1").fetchone()
row_nuggets  = conn.execute("SELECT id FROM dish WHERE LOWER(name) LIKE '%nuggets%' AND active=1 LIMIT 1").fetchone()
row_chamorro = conn.execute(
    "SELECT d.id FROM dish d JOIN dish_tag dt ON d.id=dt.dish_id "
    "WHERE dt.tag='friday_chamorro' AND d.active=1 LIMIT 1"
).fetchone()

PANCITA_ID  = row_pancita['id']
PAELLA_ID   = row_paella['id']
NUGGETS_ID  = row_nuggets['id']
CHAMORRO_ID = row_chamorro['id'] if row_chamorro else None

print(f'\nFixed: COMAL={COMAL_ID} ARROZ={ARROZ_ID} PANCITA={PANCITA_ID} '
      f'PAELLA={PAELLA_ID} NUGGETS={NUGGETS_ID} CHAMORRO={CHAMORRO_ID}')

# Conflictos resueltos: ya existen con otro ID
CREMA_CHICHARRON_ID = 503    # "Crema de Chicharrón" ya existía (skip rename 1545)
CHILE_RELLENO_ID    = 1510   # "Chile Relleno de Queso" ya existía (skip rename 1106)
CREMA_JALAPENO_ID   = id_crema_jalapeno  # 1358 (skip create, ya existía)
FILETE_MANTEQUILLA_ID = id_filete_mantequilla  # 1389 (skip create, ya existía)

# ─────────────────────────────────────────────────────
# 4) Insertar semana 2026-02-09
# ─────────────────────────────────────────────────────
print('\n=== INSERTAR SEMANA 2026-02-09 ===')

WEEK_START = date(2026, 2, 9)

existing = conn.execute('SELECT id FROM menu_week WHERE week_start_date=?', (str(WEEK_START),)).fetchone()
if existing:
    print(f'  Semana ya existe (id={existing["id"]}), abortando')
    conn.close()
    sys.exit(0)

from datetime import datetime
week_id = conn.execute(
    'INSERT INTO menu_week (week_start_date, generated_at, finalized) VALUES (?,?,1)',
    (str(WEEK_START), datetime.now().isoformat())
).lastrowid
print(f'  menu_week id={week_id}')

def item(d: date, slot: str, dish_id):
    if dish_id is None:
        print(f'  SKIP {d} {slot} (None)')
        return
    conn.execute(
        'INSERT INTO menu_item (menu_week_id, menu_date, slot, dish_id, was_exception) VALUES (?,?,?,?,0)',
        (week_id, str(d), slot, dish_id)
    )

mon = WEEK_START
tue = WEEK_START + timedelta(1)
wed = WEEK_START + timedelta(2)
thu = WEEK_START + timedelta(3)
fri = WEEK_START + timedelta(4)
sat = WEEK_START + timedelta(5)

# LUNES (molcajete=cerdo → no fuerte_cerdo)
item(mon, 'entrada_comal',    COMAL_ID)
item(mon, 'entrada_no_comal', 1454)
item(mon, 'crema',            504)
item(mon, 'sopa',             481)
item(mon, 'pasta',            id_pasta_almeja)
item(mon, 'ensalada_A',       1278)
item(mon, 'arroz',            ARROZ_ID)
item(mon, 'molcajete',        id_molcajete_enchilada)
item(mon, 'fuerte_res',       922)
item(mon, 'fuerte_pollo',     1291)
item(mon, 'fuerte_pescado',   674)
item(mon, 'fuerte_camaron',   746)
item(mon, 'complemento',      1089)

# MARTES (sin fuerte_pollo ese día)
item(tue, 'entrada_comal',    COMAL_ID)
item(tue, 'entrada_no_comal', 1171)
item(tue, 'crema',            CREMA_JALAPENO_ID)
item(tue, 'sopa',             427)
item(tue, 'pasta',            id_espagueti_finas)
item(tue, 'ensalada_B',       1157)
item(tue, 'arroz',            ARROZ_ID)
item(tue, 'fuerte_res',       id_huarache_costilla)
item(tue, 'fuerte_cerdo',     1397)
item(tue, 'fuerte_camaron',   id_tacos_camaron_guac)
item(tue, 'fuerte_pescado',   662)
item(tue, 'complemento',      1543)

# MIÉRCOLES
item(wed, 'entrada_comal',    COMAL_ID)
item(wed, 'entrada_no_comal', 1209)
item(wed, 'crema',            519)
item(wed, 'sopa',             547)
item(wed, 'pasta',            id_fusilli_olivo)
item(wed, 'ensalada_C',       1268)
item(wed, 'arroz',            ARROZ_ID)
item(wed, 'fuerte_res',       id_parrillada_agujas)
item(wed, 'fuerte_pollo',     1006)
item(wed, 'fuerte_cerdo',     1479)
item(wed, 'fuerte_pescado',   id_filete_aceituna)
item(wed, 'fuerte_camaron',   1261)
item(wed, 'complemento',      1075)

# JUEVES
item(thu, 'entrada_comal',    COMAL_ID)
item(thu, 'entrada_no_comal', id_montadito_espinaca)
item(thu, 'crema',            490)
item(thu, 'sopa',             1316)
item(thu, 'pasta',            id_fetuccini_pesto)
item(thu, 'ensalada_A',       1278)
item(thu, 'arroz',            ARROZ_ID)
item(thu, 'fuerte_res',       id_bistec_res)
item(thu, 'fuerte_pollo',     1036)
item(thu, 'fuerte_cerdo',     id_cerdo_pipian)
item(thu, 'fuerte_pescado',   FILETE_MANTEQUILLA_ID)
item(thu, 'fuerte_camaron',   730)
item(thu, 'complemento',      id_torta_jamon)

# VIERNES
item(fri, 'entrada_comal',    COMAL_ID)
item(fri, 'entrada_no_comal', 1562)
item(fri, 'crema',            CREMA_CHICHARRON_ID)
item(fri, 'sopa',             543)
item(fri, 'pasta',            557)
item(fri, 'ensalada_B',       1157)
item(fri, 'arroz',            ARROZ_ID)
item(fri, 'chamorro',         CHAMORRO_ID)
item(fri, 'fuerte_res',       1613)
item(fri, 'fuerte_pollo',     1003)
item(fri, 'fuerte_cerdo',     1506)
item(fri, 'fuerte_pescado',   id_filete_cremosa_esp)
item(fri, 'fuerte_camaron',   715)
item(fri, 'complemento',      CHILE_RELLENO_ID)

# SÁBADO
item(sat, 'entrada_comal',    COMAL_ID)
item(sat, 'entrada_no_comal', 1240)
item(sat, 'pancita',          PANCITA_ID)
item(sat, 'crema',            496)
item(sat, 'sopa_pollo',       1612)
item(sat, 'ensalada_C',       id_ensalada_paraiso)
item(sat, 'pasta',            id_fusilli_olivo)
item(sat, 'fuerte_res',       908)
item(sat, 'fuerte_pollo',     982)
item(sat, 'fuerte_cerdo',     1321)
item(sat, 'paella',           PAELLA_ID)
item(sat, 'pescado_al_gusto', id_filete_vino_almejas)
item(sat, 'camaron_al_gusto', 739)
item(sat, 'nuggets',          NUGGETS_ID)
item(sat, 'enchiladas',       1221)

conn.commit()

total = conn.execute('SELECT COUNT(*) FROM menu_item WHERE menu_week_id=?', (week_id,)).fetchone()[0]
print(f'\n  ✓ Semana 2026-02-09 insertada — {total} items')

for d_str in ['2026-02-09','2026-02-10','2026-02-11','2026-02-12','2026-02-13','2026-02-14']:
    n = conn.execute('SELECT COUNT(*) FROM menu_item WHERE menu_week_id=? AND menu_date=?',
                     (week_id, d_str)).fetchone()[0]
    print(f'  {d_str}: {n} slots')

conn.close()
print('\nDone.')
