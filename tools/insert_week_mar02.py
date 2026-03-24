#!/usr/bin/env python3
"""Renames + creates + inserta semana 2026-03-02"""
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
rename(852,  'Longaniza en Salsa Verde con Frijoles de la Olla')
rename(678,  'Filete de Pescado a la Mantequilla Negra con Puré de Papa')
rename(421,  'Sopa de Pasta Munición')
rename(1335, 'Filete de Pescado Sol con Ensalada')

# ── CREATES ──
print('\n=== CREATES ===')
id_quesadilla_requeson   = gc('Quesadilla Frita de Requesón',                          'entrada',      'none')
id_crema_papa_tocino     = gc('Crema de Papa con Tocino',                              'crema',        'none')
id_ensalada_verde_mango  = gc('Ensalada Verde con Mango',                              'ensalada',     'none')
id_molcajete_agujas      = gc('Molcajete de Agujas Norteñas',                          'fuerte',       'res',
                               tags=['monday_molcajete'])
id_cerdo_guajillo        = gc('Cerdo en Guajillo con Nopales',                         'fuerte',       'cerdo')
id_filete_aguacate       = gc('Filete de Pescado en Salsa de Aguacate',                'fuerte',       'pescado')
id_pollo_tatemada        = gc('Pollo en Salsa Tatemada',                               'fuerte',       'pollo')
id_camarones_jalapeno    = gc('Camarones con Jalapeño',                                'fuerte',       'camaron')
id_colita_adobo          = gc('Colita de Res en Adobo',                                'fuerte',       'res')
id_filete_cremosa_champ  = gc('Filete de Pescado en Salsa Cremosa de Champiñones',     'fuerte',       'pescado')
id_nopal_empanizado      = gc('Nopal Empanizado Relleno de Queso en Espejo de Guajillo','complemento', 'none')
id_mini_tostadas_surimi  = gc('Mini Tostadas de Surimi',                               'entrada',      'pescado')
id_torta_queso_puerco    = gc('Torta de Queso de Puerco',                              'complemento',  'cerdo')
id_consome_ranchero      = gc('Consomé Ranchero',                                      'sopa',         'pollo')
id_espagueti_tres_quesos = gc('Espagueti a los Tres Quesos',                           'pasta',        'none')

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
print('\n=== INSERTAR SEMANA 2026-03-02 ===')
WEEK_START = date(2026, 3, 2)
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
item(mon,'entrada_no_comal', id_quesadilla_requeson)
item(mon,'crema',            id_crema_papa_tocino)
item(mon,'sopa',             1475)               # Sopa de Nopal
item(mon,'pasta',            562)                # Codito Frio
item(mon,'ensalada_A',       id_ensalada_verde_mango)
item(mon,'arroz',            ARROZ_ID)
item(mon,'molcajete',        id_molcajete_agujas)
item(mon,'fuerte_cerdo',     id_cerdo_guajillo)
item(mon,'fuerte_pollo',     1507)               # Pechuga de Pollo Rellena de Elote con Queso
item(mon,'fuerte_camaron',   733)                # Camarones al Tequila
item(mon,'fuerte_pescado',   id_filete_aguacate)
item(mon,'complemento',      1543)               # Croquetas de Atun con Ensalada

# MARTES
item(tue,'entrada_comal',    COMAL_ID)
item(tue,'entrada_no_comal', 1175)               # Gordita de Chicharron
item(tue,'crema',            520)                # Crema de Flor de Calabaza
item(tue,'sopa',             453)                # Sopa Poblana
item(tue,'pasta',            1329)               # Fusilli Pesto
item(tue,'ensalada_B',       1577)               # Ensalada de Piña con Arandanos
item(tue,'arroz',            ARROZ_ID)
item(tue,'fuerte_res',       1458)               # Tacos de Gaonera
item(tue,'fuerte_cerdo',     852)                # Longaniza en Salsa Verde (renamed)
item(tue,'fuerte_pollo',     id_pollo_tatemada)
item(tue,'fuerte_camaron',   id_camarones_jalapeno)
item(tue,'fuerte_pescado',   678)                # Filete Mantequilla Negra (renamed)
item(tue,'complemento',      1089)               # Enchiladas Mineras

# MIÉRCOLES
item(wed,'entrada_comal',    COMAL_ID)
item(wed,'entrada_no_comal', 1171)               # Taco Placero
item(wed,'crema',            162)                # Crema de Zanahoria
item(wed,'sopa',             1359)               # Sopa de Alubias
item(wed,'pasta',            583)                # Espagueti al Mojo
item(wed,'ensalada_C',       1341)               # Calabacitas Grill
item(wed,'arroz',            ARROZ_ID)
item(wed,'fuerte_res',       id_colita_adobo)
item(wed,'fuerte_cerdo',     1578)               # Pierna de Cerdo al Horno con Pure de Papa
item(wed,'fuerte_pollo',     991)                # Pollo en Salsa Borracha
item(wed,'fuerte_camaron',   1301)               # Tacos Gobernador
item(wed,'fuerte_pescado',   id_filete_cremosa_champ)
item(wed,'complemento',      id_nopal_empanizado)

# JUEVES
item(thu,'entrada_comal',    COMAL_ID)
item(thu,'entrada_no_comal', 1179)               # Tlacoyo de Frijol
item(thu,'crema',            536)                # Crema de Espinaca con Nuez
item(thu,'sopa',             422)                # Sopa de Cebolla
item(thu,'pasta',            421)                # Sopa de Pasta Municion (renamed)
item(thu,'ensalada_A',       id_ensalada_verde_mango)
item(thu,'arroz',            ARROZ_ID)
item(thu,'fuerte_res',       1331)               # Costilla de Res con Chilaquiles
item(thu,'fuerte_cerdo',     1269)               # Carne Enchilada con Guacamole y Frijoles
item(thu,'fuerte_pollo',     1036)               # Pollo a la Barbacoa
item(thu,'fuerte_camaron',   723)                # Alambre de Camaron
item(thu,'fuerte_pescado',   1335)               # Filete de Pescado Sol con Ensalada (renamed)
item(thu,'complemento',      1075)               # Tortitas de Espinaca Rellenas de Queso en Salsa Verde

# VIERNES
item(fri,'entrada_comal',    COMAL_ID)
item(fri,'entrada_no_comal', id_mini_tostadas_surimi)
item(fri,'crema',            491)                # Crema Conde
item(fri,'sopa',             1610)               # Chilpachole de Jaiba
item(fri,'pasta',            1288)               # Fetuccini al Aglio Olio
item(fri,'ensalada_B',       1577)               # Ensalada de Piña con Arandanos
item(fri,'arroz',            ARROZ_ID)
item(fri,'chamorro',         CHAMORRO_ID)
item(fri,'fuerte_res',       900)                # Entomatado de Res
item(fri,'fuerte_cerdo',     1592)               # Machitos de Carnero con Guacamole
item(fri,'fuerte_pollo',     1517)               # Pechuga de Pollo al Chimichurri
item(fri,'fuerte_camaron',   726)                # Tortitas de Atun en Salsa de Chile Pasilla
item(fri,'fuerte_pescado',   1364)               # Filete de Pescado Empanizado con Ensalada
item(fri,'complemento',      id_torta_queso_puerco)

# SÁBADO
item(sat,'entrada_comal',    COMAL_ID)
item(sat,'entrada_no_comal', 1411)               # Pambacito
item(sat,'pancita',          PANCITA_ID)
item(sat,'crema',            532)                # Crema de Esquites
item(sat,'sopa_pollo',       id_consome_ranchero)
item(sat,'ensalada_C',       1341)               # Calabacitas Grill
item(sat,'pasta',            id_espagueti_tres_quesos)
item(sat,'fuerte_res',       1593)               # Hamburguesa Tradicional con Tocino
item(sat,'fuerte_cerdo',     826)                # Costillas BBQ
item(sat,'fuerte_pollo',     1480)               # Pechuga de Pollo Oaxaqueña
item(sat,'paella',           PAELLA_ID)
item(sat,'pescado_al_gusto', 1310)               # Filete de Pescado al Gusto
item(sat,'camaron_al_gusto', 1365)               # Aguachile de Camaron al Gusto
item(sat,'nuggets',          NUGGETS_ID)
item(sat,'enchiladas',       994)                # Enchiladas Suizas

conn.commit()

total = conn.execute('SELECT COUNT(*) FROM menu_item WHERE menu_week_id=?', (week_id,)).fetchone()[0]
print(f'\n  ✓ Semana 2026-03-02 insertada — {total} items')
for d_str in ['2026-03-02','2026-03-03','2026-03-04','2026-03-05','2026-03-06','2026-03-07']:
    n = conn.execute('SELECT COUNT(*) FROM menu_item WHERE menu_week_id=? AND menu_date=?',
                     (week_id, d_str)).fetchone()[0]
    print(f'  {d_str}: {n} slots')

conn.close()
print('\nDone.')
