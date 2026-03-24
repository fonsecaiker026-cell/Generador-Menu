#!/usr/bin/env python3
"""Renames + creates + inserta semana 2025-03-09"""
import sqlite3, sys
from datetime import date, timedelta, datetime

sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('data/app.db')
conn.row_factory = sqlite3.Row
conn.execute('PRAGMA foreign_keys = ON')

def rename(dish_id, new_name):
    old = conn.execute('SELECT name FROM dish WHERE id=?', (dish_id,)).fetchone()
    if not old: return
    if old['name'] == new_name:
        print(f'  SKIP [{dish_id}] ya ok')
        return
    dup = conn.execute('SELECT id FROM dish WHERE name=? AND id!=?', (new_name, dish_id)).fetchone()
    if dup:
        print(f'  WARN dup "{new_name}" existe como {dup["id"]}')
        return
    conn.execute('UPDATE dish SET name=? WHERE id=?', (new_name, dish_id))
    print(f'  RENAME [{dish_id}] → "{new_name}"')

def gc(name, course_group, protein, tags=None):
    r = conn.execute('SELECT id FROM dish WHERE LOWER(name)=LOWER(?)', (name,)).fetchone()
    if r:
        print(f'  SKIP (existe) [{r["id"]}] "{name}"')
        return r['id']
    c = conn.execute('INSERT INTO dish (name,course_group,protein,active) VALUES (?,?,?,1)',
                     (name, course_group, protein))
    i = c.lastrowid
    if tags:
        for t in tags:
            conn.execute('INSERT OR IGNORE INTO dish_tag (dish_id,tag) VALUES (?,?)', (i, t))
    print(f'  CREATE [{i}] "{name}"')
    return i

def gid(name):
    r = conn.execute('SELECT id FROM dish WHERE LOWER(name)=LOWER(?)', (name,)).fetchone()
    if not r:
        print(f'  ERROR no encontrado: "{name}"'); return None
    return r['id']

# ── RENAMES ──
print('\n=== RENAMES ===')
rename(1636, 'Fusilli a las Finas Hierbas')
rename(1146, 'Ensalada Rusa con Atún')
rename(1120, 'Chilaquiles Leñador con Pollo o Huevo')
rename(1641, 'Bistec de Res Encebollado con Frijoles')
rename(1585, 'Filete de Pescado al Ajo, Limón y Especias con Puré de Papa')

# ── CREATES ──
print('\n=== CREATES ===')
id_pollo_chipotle       = gc('Pollo en Salsa Cremosa de Chipotle',             'fuerte',      'pollo')
id_picana_toreados      = gc('Picaña a la Parrilla con Chiles Toreados',       'fuerte',      'res')
id_ensalada_melon       = gc('Ensalada de Melón, Zanahoria y Nuez',            'ensalada',    'none')
id_rollitos_jamon       = gc('Rollitos de Jamón con Guacamole',                'entrada',     'cerdo')
id_costilla_morita      = gc('Costilla de Cerdo en Salsa de Chile Morita con Papas', 'fuerte','cerdo')
id_pescadillas          = gc('Pescadillas',                                    'entrada',     'pescado')
id_pasta_jalapeno       = gc('Pasta Pluma con Jalapeño',                       'pasta',       'none')
id_chicharron_frijoles  = gc('Chicharrón en Salsa Verde con Frijoles de la Olla','fuerte',   'cerdo')
id_espagueti_burro      = gc('Espagueti al Burro',                             'pasta',       'none')
id_carne_chilaquiles    = gc('Carne Enchilada con Chilaquiles',                'fuerte',      'res')

conn.commit()

# ── IDs fijos y lookups ──
COMAL_ID    = 202
ARROZ_ID    = 1596
PANCITA_ID  = conn.execute("SELECT id FROM dish WHERE LOWER(name) LIKE '%pancita%' AND active=1 LIMIT 1").fetchone()['id']
PAELLA_ID   = conn.execute("SELECT id FROM dish WHERE LOWER(name) LIKE '%paella%' AND active=1 LIMIT 1").fetchone()['id']
NUGGETS_ID  = conn.execute("SELECT id FROM dish WHERE LOWER(name) LIKE '%nuggets%' AND active=1 LIMIT 1").fetchone()['id']
CHAMORRO_ID = conn.execute("SELECT d.id FROM dish d JOIN dish_tag dt ON d.id=dt.dish_id WHERE dt.tag='friday_chamorro' AND d.active=1 LIMIT 1").fetchone()['id']
FILETE_ACEITUNA_ID = conn.execute("SELECT id FROM dish WHERE LOWER(name) LIKE '%aceituna%' AND active=1 LIMIT 1").fetchone()['id']
print(f'\nFixed: COMAL={COMAL_ID} ARROZ={ARROZ_ID} PANCITA={PANCITA_ID} PAELLA={PAELLA_ID} NUGGETS={NUGGETS_ID} CHAMORRO={CHAMORRO_ID}')
print(f'  Filete Aceituna={FILETE_ACEITUNA_ID}')

# ── SEMANA ──
print('\n=== INSERTAR SEMANA 2025-03-09 ===')
WEEK_START = date(2025, 3, 9)
existing = conn.execute('SELECT id FROM menu_week WHERE week_start_date=?', (str(WEEK_START),)).fetchone()
if existing:
    print(f'  Ya existe id={existing["id"]}, abortando'); conn.close(); sys.exit(0)

week_id = conn.execute(
    'INSERT INTO menu_week (week_start_date, generated_at, finalized) VALUES (?,?,1)',
    (str(WEEK_START), datetime.now().isoformat())
).lastrowid
print(f'  week_id={week_id}')

def item(d, slot, dish_id):
    if dish_id is None: return
    conn.execute('INSERT INTO menu_item (menu_week_id,menu_date,slot,dish_id,was_exception) VALUES (?,?,?,?,0)',
                 (week_id, str(d), slot, dish_id))

mon,tue,wed,thu,fri,sat = [WEEK_START + timedelta(i) for i in range(6)]

# LUNES — molcajete=cerdo (Oreja Elefante) → sin fuerte_cerdo
item(mon,'entrada_comal',    COMAL_ID)
item(mon,'entrada_no_comal', 1244)               # Montadito de Champiñones con Espinaca y Queso
item(mon,'crema',            490)                # Crema de Cilantro
item(mon,'sopa',             485)                # Sopa de Milpa
item(mon,'pasta',            1371)               # Espagueti Alfredo
item(mon,'ensalada_A',       1436)               # Ensalada de Espinaca con Naranja
item(mon,'arroz',            ARROZ_ID)
item(mon,'molcajete',        1385)               # Molcajete de Oreja de Elefante
item(mon,'fuerte_res',       901)                # Flautas de Res
item(mon,'fuerte_pollo',     id_pollo_chipotle)
item(mon,'fuerte_camaron',   1261)               # Camarones a la Talla
item(mon,'fuerte_pescado',   FILETE_ACEITUNA_ID) # Filete de Pescado en Salsa de Aceituna Negra
item(mon,'complemento',      1263)               # Enfrijoladas Veracruzanas

# MARTES
item(tue,'entrada_comal',    COMAL_ID)
item(tue,'entrada_no_comal', 1313)               # Quesadilla Frita de Frijol
item(tue,'crema',            522)                # Crema de Calabaza con Chile Ancho
item(tue,'sopa',             156)                # Sopa de Verduras
item(tue,'pasta',            1636)               # Fusilli a las Finas Hierbas (renamed)
item(tue,'ensalada_B',       1146)               # Ensalada Rusa con Atún (renamed)
item(tue,'arroz',            ARROZ_ID)
item(tue,'fuerte_res',       id_picana_toreados)
item(tue,'fuerte_cerdo',     892)                # Torta de Pierna
item(tue,'fuerte_pollo',     1439)               # Pechuga de Pollo Napolitana
item(tue,'fuerte_camaron',   746)                # Camarones Costa Brava
item(tue,'fuerte_pescado',   632)                # Filete de Pescado al Ajillo
item(tue,'complemento',      1101)               # Enchiladas Potosinas

# MIÉRCOLES
item(wed,'entrada_comal',    COMAL_ID)
item(wed,'entrada_no_comal', 1337)               # Tetela de Queso
item(wed,'crema',            503)                # Crema de Chicharrón
item(wed,'sopa',             481)                # Sopa de Champiñones
item(wed,'pasta',            159)                # Sopa Minestrone
item(wed,'ensalada_C',       id_ensalada_melon)
item(wed,'arroz',            ARROZ_ID)
item(wed,'fuerte_res',       926)                # Parrillada de Arrachera
item(wed,'fuerte_cerdo',     1558)               # Espinazo de Cerdo en Pipián con Chilacayote
item(wed,'fuerte_pollo',     1281)               # Pollo en Salsa Molcajeteada
item(wed,'fuerte_camaron',   749)                # Camarones al Vino Blanco
item(wed,'fuerte_pescado',   658)                # Tacos de Pescado Estilo Ensenada(Capeado)
item(wed,'complemento',      1120)               # Chilaquiles Leñador con Pollo o Huevo (renamed)

# JUEVES
item(thu,'entrada_comal',    COMAL_ID)
item(thu,'entrada_no_comal', id_rollitos_jamon)
item(thu,'crema',            436)                # Sopa Tarasca
item(thu,'sopa',             427)                # Sopa de Ajo
item(thu,'pasta',            562)                # Codito Frío
item(thu,'ensalada_A',       1436)               # Ensalada de Espinaca con Naranja
item(thu,'arroz',            ARROZ_ID)
item(thu,'fuerte_res',       1641)               # Bistec de Res Encebollado con Frijoles (renamed)
item(thu,'fuerte_cerdo',     id_costilla_morita)
item(thu,'fuerte_pollo',     1046)               # Huarache de Tinga de Pollo
item(thu,'fuerte_camaron',   1588)               # Camarones Enchilados al Sartén con Queso
item(thu,'fuerte_pescado',   1585)               # Filete de Pescado al Ajo, Limón y Especias con Puré de Papa (renamed)
item(thu,'complemento',      1096)               # Tacos Dorados de Papa Ahogados

# VIERNES
item(fri,'entrada_comal',    COMAL_ID)
item(fri,'entrada_no_comal', id_pescadillas)
item(fri,'crema',            1563)               # Crema de Coliflor con un Toque de Miel
item(fri,'sopa',             157)                # Sopa Azteca
item(fri,'pasta',            id_pasta_jalapeno)
item(fri,'ensalada_B',       1146)               # Ensalada Rusa con Atún
item(fri,'arroz',            ARROZ_ID)
item(fri,'chamorro',         CHAMORRO_ID)
item(fri,'fuerte_res',       1613)               # Albóndigas al Chipotle
item(fri,'fuerte_cerdo',     id_chicharron_frijoles)
item(fri,'fuerte_pollo',     1630)               # Pechuga de Pollo Empanizada con Ensalada
item(fri,'fuerte_camaron',   730)                # Camarones a la Diabla
item(fri,'fuerte_pescado',   1462)               # Filete de Pescado Rockefeller
item(fri,'complemento',      1510)               # Chile Relleno de Queso

# SÁBADO
item(sat,'entrada_comal',    COMAL_ID)
item(sat,'entrada_no_comal', 1251)               # Chalupas Mixtas
item(sat,'pancita',          PANCITA_ID)
item(sat,'crema',            163)                # Crema Poblana
item(sat,'sopa_pollo',       540)                # Caldo Tlalpeño
item(sat,'ensalada_C',       id_ensalada_melon)
item(sat,'pasta',            id_espagueti_burro)
item(sat,'fuerte_res',       1351)               # Tacos de Suadero
item(sat,'fuerte_cerdo',     id_carne_chilaquiles)
item(sat,'fuerte_pollo',     1450)               # Pechuga de Pollo Rellena de Espinacas con Queso
item(sat,'paella',           PAELLA_ID)
item(sat,'pescado_al_gusto', 1310)               # Filete de Pescado al Gusto
item(sat,'camaron_al_gusto', 739)                # Camarones al Coco con Dip de Mango
item(sat,'nuggets',          NUGGETS_ID)
item(sat,'enchiladas',       1568)               # Enchiladas Divorciadas

conn.commit()

total = conn.execute('SELECT COUNT(*) FROM menu_item WHERE menu_week_id=?', (week_id,)).fetchone()[0]
print(f'\n  ✓ Semana 2025-03-09 insertada — {total} items')
for d_str in ['2025-03-09','2025-03-10','2025-03-11','2025-03-12','2025-03-13','2025-03-14']:
    n = conn.execute('SELECT COUNT(*) FROM menu_item WHERE menu_week_id=? AND menu_date=?',
                     (week_id, d_str)).fetchone()[0]
    print(f'  {d_str}: {n} slots')

conn.close()
print('\nDone.')
