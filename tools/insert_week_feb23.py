#!/usr/bin/env python3
"""Renames + creates + inserta semana 2026-02-23"""
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

# ── RENAMES ──
print('\n=== RENAMES ===')
rename(1443, 'Dobladita de Papa con Epazote')
rename(1325, 'Chilaquiles Arrieros con Pollo o Huevo')

# ── CREATES ──
print('\n=== CREATES ===')
id_filete_poblano    = gc('Filete de Pescado en Salsa Cremosa de Poblano con Elote', 'fuerte', 'pescado')
id_tostadas_res      = gc('Mini Tostadas de Tinga de Res',              'entrada',      'res')
id_fusilli_crema     = gc('Fusilli con Verduras a la Crema',             'pasta',        'none')
id_ensalada_cesar    = gc('Ensalada Cesar',                              'ensalada',     'none')
id_filete_bechamel   = gc('Filete de Pescado en Salsa de Bechamel',      'fuerte',       'pescado')
id_agujas_guacamole  = gc('Agujas Norteñas con Guacamole y Frijoles Refritos', 'fuerte', 'res')
id_pechuga_romero    = gc('Pechuga de Pollo al Romero con Puré de Papa', 'fuerte',       'pollo')
id_bombas_camaron    = gc('Bombas de Camarón',                           'fuerte',       'camaron')
id_tortitas_huauz    = gc('Tortitas de Huauzontle en Caldillo de Jitomate', 'complemento', 'none')
id_huevo_atun        = gc('Huevo Relleno de Atún',                       'entrada',      'pescado')
id_chicharron_verde  = gc('Chicharrón en Salsa Verde con Nopales',       'fuerte',       'cerdo')
id_chile_camaron     = gc('Chile Relleno de Camarón',                    'fuerte',       'camaron')
id_filete_empap      = gc('Filete de Pescado Empapelado con Chile Ancho','fuerte',       'pescado')
id_cuaresm_queso     = gc('Cuaresmeño Relleno de Queso',                 'entrada',      'none')
id_costilla_verde    = gc('Costilla de Cerdo en Salsa Verde con Verdolagas', 'fuerte',   'cerdo')
id_arrachera_frijol  = gc('Arrachera con Frijoles y Pico de Gallo',      'fuerte',       'res')
id_tacos_chuleta     = gc('Tacos de Chuleta con Nopales y Cebolla',      'fuerte',       'cerdo')
id_consome_chile     = gc('Consomé de Pollo con Chile de Árbol',         'sopa',         'pollo')

conn.commit()

# ── IDs fijos ──
COMAL_ID   = 202
ARROZ_ID   = 1596
PANCITA_ID = conn.execute("SELECT id FROM dish WHERE LOWER(name) LIKE '%pancita%' AND active=1 LIMIT 1").fetchone()['id']
PAELLA_ID  = conn.execute("SELECT id FROM dish WHERE LOWER(name) LIKE '%paella%' AND active=1 LIMIT 1").fetchone()['id']
NUGGETS_ID = conn.execute("SELECT id FROM dish WHERE LOWER(name) LIKE '%nuggets%' AND active=1 LIMIT 1").fetchone()['id']
CHAMORRO_ID= conn.execute("SELECT d.id FROM dish d JOIN dish_tag dt ON d.id=dt.dish_id WHERE dt.tag='friday_chamorro' AND d.active=1 LIMIT 1").fetchone()['id']
print(f'\nFixed: COMAL={COMAL_ID} ARROZ={ARROZ_ID} PANCITA={PANCITA_ID} PAELLA={PAELLA_ID} NUGGETS={NUGGETS_ID} CHAMORRO={CHAMORRO_ID}')

# ── SEMANA ──
print('\n=== INSERTAR SEMANA 2026-02-23 ===')
WEEK_START = date(2026, 2, 23)
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

# LUNES — molcajete=res → sin fuerte_res
item(mon,'entrada_comal',    COMAL_ID)
item(mon,'entrada_no_comal', 1443)               # Dobladita de Papa con Epazote
item(mon,'crema',            1358)               # Crema de Jalapeño con Queso
item(mon,'sopa',             432)                # Sopa de Setas
item(mon,'pasta',            1556)               # Espagueti al Ajillo
item(mon,'ensalada_A',       1166)               # Ensalada de Pepino a la Vinagreta
item(mon,'arroz',            ARROZ_ID)
item(mon,'molcajete',        1426)               # Molcajete de Arrachera (res)
item(mon,'fuerte_cerdo',     1352)               # Bistec de Cerdo en Salsa de Chile Pasilla
item(mon,'fuerte_pollo',     1517)               # Pechuga de Pollo al Chimichurri
item(mon,'fuerte_camaron',   1334)               # Camarones al Cilantro y Chile Limón
item(mon,'fuerte_pescado',   id_filete_poblano)  # Filete Cremosa de Poblano con Elote
item(mon,'complemento',      1356)               # Enchiladas Queretanas de Queso

# MARTES
item(tue,'entrada_comal',    COMAL_ID)
item(tue,'entrada_no_comal', id_tostadas_res)    # Mini Tostadas de Tinga de Res
item(tue,'crema',            494)                # Crema de Brócoli
item(tue,'sopa',             446)                # Sopa de Calabacitas con Poblano
item(tue,'pasta',            id_fusilli_crema)   # Fusilli con Verduras a la Crema
item(tue,'ensalada_B',       id_ensalada_cesar)  # Ensalada Cesar
item(tue,'arroz',            ARROZ_ID)
item(tue,'fuerte_res',       950)                # Mole de Olla
item(tue,'fuerte_cerdo',     1584)               # Chuleta en Salsa de Piña y Chipotle
item(tue,'fuerte_pollo',     989)                # Pollo en Salsa Pibil
item(tue,'fuerte_camaron',   1440)               # Tacos de Camaron Tradicional
item(tue,'fuerte_pescado',   id_filete_bechamel) # Filete en Salsa de Bechamel
item(tue,'complemento',      1325)               # Chilaquiles Arrieros con Pollo o Huevo

# MIÉRCOLES
item(wed,'entrada_comal',    COMAL_ID)
item(wed,'entrada_no_comal', 1525)               # Nopal Tradicional
item(wed,'crema',            493)                # Crema de Pimiento
item(wed,'sopa',             1393)               # Sopa de Poro y Papa
item(wed,'pasta',            564)                # Codito con Espinaca
item(wed,'ensalada_C',       1477)               # Ensalada de Espinaca con Melón
item(wed,'arroz',            ARROZ_ID)
item(wed,'fuerte_res',       id_agujas_guacamole)# Agujas Norteñas con Guacamole y Frijoles
item(wed,'fuerte_cerdo',     893)                # Torta de Cochinita
item(wed,'fuerte_pollo',     id_pechuga_romero)  # Pechuga al Romero con Puré
item(wed,'fuerte_camaron',   id_bombas_camaron)  # Bombas de Camarón
item(wed,'fuerte_pescado',   1283)               # Filete de Pescado al Pastor
item(wed,'complemento',      id_tortitas_huauz)  # Tortitas de Huauzontle

# JUEVES
item(thu,'entrada_comal',    COMAL_ID)
item(thu,'entrada_no_comal', id_huevo_atun)      # Huevo Relleno de Atún
item(thu,'crema',            160)                # Crema de Champiñones
item(thu,'sopa',             438)                # Sopa Campesina
item(thu,'pasta',            1435)               # Pasta Pluma Pomodoro
item(thu,'ensalada_A',       1166)               # Ensalada de Pepino a la Vinagreta
item(thu,'arroz',            ARROZ_ID)
item(thu,'fuerte_res',       1351)               # Tacos de Suadero
item(thu,'fuerte_cerdo',     id_chicharron_verde)# Chicharrón en Salsa Verde con Nopales
item(thu,'fuerte_pollo',     985)                # Pollo Asado Enchilado
item(thu,'fuerte_camaron',   id_chile_camaron)   # Chile Relleno de Camarón
item(thu,'fuerte_pescado',   id_filete_empap)    # Filete Empapelado con Chile Ancho
item(thu,'complemento',      1284)               # Tacos Dorados Mixtos

# VIERNES
item(fri,'entrada_comal',    COMAL_ID)
item(fri,'entrada_no_comal', id_cuaresm_queso)   # Cuaresmeño Relleno de Queso
item(fri,'crema',            495)                # Crema de Almeja
item(fri,'sopa',             1287)               # Sopa de Habas
item(fri,'pasta',            155)                # Sopa de Fideo
item(fri,'ensalada_B',       1425)               # Ensalada de Zanahoria
item(fri,'arroz',            ARROZ_ID)
item(fri,'chamorro',         CHAMORRO_ID)
item(fri,'fuerte_res',       1298)               # Milanesa de Res con Ensalada
item(fri,'fuerte_cerdo',     id_costilla_verde)  # Costilla de Cerdo en Salsa Verde con Verdolagas
item(fri,'fuerte_pollo',     1450)               # Pechuga Rellena de Espinacas con Queso
item(fri,'fuerte_camaron',   741)                # Camarones Roca
item(fri,'fuerte_pescado',   1345)               # Filete en Salsa Cremosa de Cilantro
item(fri,'complemento',      1094)               # Romeritos

# SÁBADO
item(sat,'entrada_comal',    COMAL_ID)
item(sat,'entrada_no_comal', 1553)               # Pescaditos Rebozados
item(sat,'pancita',          PANCITA_ID)
item(sat,'crema',            160)                # Crema de Champiñones
item(sat,'sopa_pollo',       id_consome_chile)   # Consomé de Pollo con Chile de Árbol
item(sat,'ensalada_C',       1477)               # Ensalada de Espinaca con Melón
item(sat,'pasta',            579)                # Espagueti Verde
item(sat,'fuerte_res',       id_arrachera_frijol)# Arrachera con Frijoles y Pico de Gallo
item(sat,'fuerte_cerdo',     id_tacos_chuleta)   # Tacos de Chuleta con Nopales y Cebolla
item(sat,'fuerte_pollo',     1630)               # Pechuga de Pollo Empanizada con Ensalada
item(sat,'paella',           PAELLA_ID)
item(sat,'pescado_al_gusto', 1310)               # Filete de Pescado al Gusto
item(sat,'camaron_al_gusto', 1376)               # Camarones Hawaianos o al Gusto
item(sat,'nuggets',          NUGGETS_ID)
item(sat,'enchiladas',       1518)               # Enchiladas de Pollo en Mole Poblano

conn.commit()

total = conn.execute('SELECT COUNT(*) FROM menu_item WHERE menu_week_id=?', (week_id,)).fetchone()[0]
print(f'\n  ✓ Semana 2026-02-23 insertada — {total} items')
for d_str in ['2026-02-23','2026-02-24','2026-02-25','2026-02-26','2026-02-27','2026-02-28']:
    n = conn.execute('SELECT COUNT(*) FROM menu_item WHERE menu_week_id=? AND menu_date=?',
                     (week_id, d_str)).fetchone()[0]
    print(f'  {d_str}: {n} slots')

conn.close()
print('\nDone.')
