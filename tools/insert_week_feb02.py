#!/usr/bin/env python3
"""
Insert historical week 2026-02-02 with renames and new dish creation.
"""
import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')

DB = 'data/app.db'
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# === STEP 1: RENAMES ===
renames = [
    (632,  'Filete de Pescado al Ajillo'),
    # 1127 NOT renamed: ID 1336 already has 'Tortitas...Caldillo de Jitomate'
    (1432, 'Cuaresmeño Relleno de Chorizo con Queso'),
    (451,  'Sopa de Flor de Calabaza con Pollo'),
    (723,  'Alambre de Camarón'),
    (1365, 'Aguachile de Camarón al Gusto'),
]
print('=== RENAMES ===')
for dish_id, new_name in renames:
    old = conn.execute('SELECT name FROM dish WHERE id=?', (dish_id,)).fetchone()
    old_name = old[0] if old else '?'
    conn.execute('UPDATE dish SET name=? WHERE id=?', (new_name, dish_id))
    print(f'  {dish_id}: {old_name!r} -> {new_name!r}')

# === STEP 2: CREATE NEW DISHES ===
new_dish_specs = [
    ('Espinazo en Salsa de Chile Cascabel',      'fuerte',      'cerdo',   None, None, []),
    ('Pechuga de Pollo al Chumichurri',           'fuerte',      'pollo',   None, None, []),
    # 'Salpicón de Res' → already exists as ID 1279
    ('Cerdo Almendrado',                          'fuerte',      'cerdo',   None, None, []),
    # 'Crema de Brócoli' → already exists as ID 494
    ('Tacos de Chicharrón de Pescado',            'fuerte',      'pescado', None, None, []),
    ('Enchiladas Tamaulipecas',                   'complemento', 'none',    'sat_enchiladas', None, ['sat_enchiladas']),
    ('Mini Tostadas de Tinga de Pollo',           'entrada',     'pollo',   None, None, []),
    ('Fettuccini con Espinaca y Queso',           'pasta',       'none',    None, None, []),
    ('Tacos Dorados de Cochinita',                'fuerte',      'cerdo',   None, None, []),
    ('Pechuga de Pollo Empanizada con Ensalada',  'fuerte',      'pollo',   None, None, []),
]
print('\n=== CREATE NEW DISHES ===')
new_ids = {}
for name, cg, protein, style_tag, sauce_tag, tags in new_dish_specs:
    cur = conn.execute(
        'INSERT INTO dish (name, course_group, protein, style_tag, sauce_tag, active) VALUES (?,?,?,?,?,1)',
        (name, cg, protein, style_tag, sauce_tag)
    )
    dish_id = cur.lastrowid
    new_ids[name] = dish_id
    for tag in tags:
        conn.execute('INSERT OR IGNORE INTO dish_tag (dish_id, tag) VALUES (?,?)', (dish_id, tag))
    print(f'  {dish_id}: {name} ({cg}/{protein})')

def D(name):
    return new_ids[name]

# Fixed IDs
COMAL_ID    = 202
ARROZ_ID    = 1596
CHAMORRO_ID = 418   # Chamorro
PANCITA_ID  = 39    # Pancita(Sabado)
PAELLA_ID   = 41    # Paella(Sabado)
NUGGETS_ID  = 44    # Nuggets(Sabado)

# === STEP 3: INSERT WEEK ===
WEEK_START = '2026-02-02'
print(f'\n=== INSERT WEEK {WEEK_START} ===')

week_id = conn.execute(
    'INSERT INTO menu_week (week_start_date, generated_at, finalized, notes) VALUES (?,datetime("now"),1,?)',
    (WEEK_START, 'Historial real registrado manualmente')
).lastrowid
print(f'  menu_week id={week_id}')

week_menu = [
    # LUNES 2026-02-02
    ('2026-02-02', 'entrada_comal',  COMAL_ID,                                  'entrada',    'none',    1),
    ('2026-02-02', 'arroz',          ARROZ_ID,                                  'arroz',      'none',    1),
    ('2026-02-02', 'ensalada_A',     1341,                                      'ensalada',   'none',    0),
    ('2026-02-02', 'molcajete',      1478,                                      'fuerte',     'res',     0),
    ('2026-02-02', 'fuerte_cerdo',   D('Espinazo en Salsa de Chile Cascabel'),  'fuerte',     'cerdo',   0),
    ('2026-02-02', 'fuerte_pollo',   D('Pechuga de Pollo al Chumichurri'),      'fuerte',     'pollo',   0),
    ('2026-02-02', 'fuerte_camaron', 1531,                                      'fuerte',     'camaron', 0),
    ('2026-02-02', 'fuerte_pescado', 632,                                       'fuerte',     'pescado', 0),
    ('2026-02-02', 'complemento',    1336,                                      'complemento','none',    0),  # Tortitas Coliflor en Caldillo de Jitomate
    # MARTES 2026-02-03
    ('2026-02-03', 'entrada_comal',    COMAL_ID, 'entrada', 'none',   1),
    ('2026-02-03', 'arroz',            ARROZ_ID, 'arroz',   'none',   1),
    ('2026-02-03', 'entrada_no_comal', 1285,     'entrada', 'none',   0),
    ('2026-02-03', 'crema',            1381,     'crema',   'none',   0),
    ('2026-02-03', 'sopa',             1475,     'sopa',    'none',   0),
    ('2026-02-03', 'pasta',            1476,     'pasta',   'none',   0),
    # MIERCOLES 2026-02-04
    ('2026-02-04', 'entrada_comal',    COMAL_ID,                        'entrada',    'none',    1),
    ('2026-02-04', 'arroz',            ARROZ_ID,                        'arroz',      'none',    1),
    ('2026-02-04', 'entrada_no_comal', 1432,                            'entrada',    'none',    0),
    ('2026-02-04', 'crema',            536,                             'crema',      'none',    0),
    ('2026-02-04', 'sopa',             451,                             'sopa',       'none',    0),
    ('2026-02-04', 'pasta',            565,                             'pasta',      'none',    0),
    ('2026-02-04', 'ensalada_C',       1395,                            'ensalada',   'none',    0),
    ('2026-02-04', 'fuerte_res',       1279,                            'fuerte',     'res',     0),  # Salpicón de Res (existing)
    ('2026-02-04', 'fuerte_cerdo',     D('Cerdo Almendrado'),           'fuerte',     'cerdo',   0),
    ('2026-02-04', 'fuerte_pollo',     1281,                            'fuerte',     'pollo',   0),
    ('2026-02-04', 'fuerte_camaron',   723,                             'fuerte',     'camaron', 0),
    ('2026-02-04', 'fuerte_pescado',   1335,                            'fuerte',     'pescado', 0),
    ('2026-02-04', 'complemento',      1134,                            'complemento','none',    0),
    # JUEVES 2026-02-05
    ('2026-02-05', 'entrada_comal',    COMAL_ID,                               'entrada',    'none',    1),
    ('2026-02-05', 'arroz',            ARROZ_ID,                               'arroz',      'none',    1),
    ('2026-02-05', 'entrada_no_comal', 1473,                                   'entrada',    'none',    0),
    ('2026-02-05', 'crema',            494,                                    'crema',      'none',    0),  # Crema de Brócoli (existing)
    ('2026-02-05', 'sopa',             456,                                    'sopa',       'none',    0),
    ('2026-02-05', 'pasta',            1414,                                   'pasta',      'none',    0),
    ('2026-02-05', 'ensalada_A',       170,                                    'ensalada',   'none',    0),
    ('2026-02-05', 'fuerte_res',       957,                                    'fuerte',     'res',     0),
    ('2026-02-05', 'fuerte_cerdo',     1539,                                   'fuerte',     'cerdo',   0),
    ('2026-02-05', 'fuerte_pollo',     991,                                    'fuerte',     'pollo',   0),
    ('2026-02-05', 'fuerte_camaron',   1488,                                   'fuerte',     'camaron', 0),
    ('2026-02-05', 'fuerte_pescado',   D('Tacos de Chicharrón de Pescado'),    'fuerte',     'pescado', 0),
    ('2026-02-05', 'complemento',      D('Enchiladas Tamaulipecas'),           'complemento','none',    0),
    # VIERNES 2026-02-06
    ('2026-02-06', 'entrada_comal',    COMAL_ID,                                        'entrada',    'none',    1),
    ('2026-02-06', 'arroz',            ARROZ_ID,                                        'arroz',      'none',    1),
    ('2026-02-06', 'chamorro',         CHAMORRO_ID,                                     'fuerte',     'cerdo',   1),
    ('2026-02-06', 'entrada_no_comal', D('Mini Tostadas de Tinga de Pollo'),            'entrada',    'pollo',   0),
    ('2026-02-06', 'sopa',             422,                                             'sopa',       'none',    0),
    ('2026-02-06', 'crema',            1611,                                            'crema',      'camaron', 0),
    ('2026-02-06', 'pasta',            D('Fettuccini con Espinaca y Queso'),            'pasta',      'none',    0),
    ('2026-02-06', 'ensalada_B',       1341,                                            'ensalada',   'none',    0),
    ('2026-02-06', 'fuerte_res',       1373,                                            'fuerte',     'res',     0),
    ('2026-02-06', 'fuerte_cerdo',     D('Tacos Dorados de Cochinita'),                'fuerte',     'cerdo',   0),
    ('2026-02-06', 'fuerte_pollo',     D('Pechuga de Pollo Empanizada con Ensalada'),  'fuerte',     'pollo',   0),
    ('2026-02-06', 'fuerte_camaron',   1541,                                            'fuerte',     'camaron', 0),
    ('2026-02-06', 'fuerte_pescado',   1462,                                            'fuerte',     'pescado', 0),
    ('2026-02-06', 'complemento',      850,                                             'complemento','none',    0),
    # SABADO 2026-02-07
    ('2026-02-07', 'entrada_comal',    COMAL_ID,   'entrada',    'none',    1),
    ('2026-02-07', 'pancita',          PANCITA_ID, 'especial',   'none',    1),
    ('2026-02-07', 'paella',           PAELLA_ID,  'especial',   'none',    1),
    ('2026-02-07', 'nuggets',          NUGGETS_ID, 'especial',   'none',    1),
    ('2026-02-07', 'entrada_no_comal', 1179,       'entrada',    'none',    0),
    ('2026-02-07', 'crema',            532,        'crema',      'none',    0),
    ('2026-02-07', 'sopa_pollo',       485,        'sopa',       'pollo',   0),
    ('2026-02-07', 'pasta',            631,        'pasta',      'none',    0),
    ('2026-02-07', 'ensalada_C',       1395,       'ensalada',   'none',    0),
    ('2026-02-07', 'fuerte_res',       912,        'fuerte',     'res',     0),
    ('2026-02-07', 'fuerte_cerdo',     887,        'fuerte',     'cerdo',   0),
    ('2026-02-07', 'fuerte_pollo',     1480,       'fuerte',     'pollo',   0),
    ('2026-02-07', 'camaron_al_gusto', 1365,       'especial',   'camaron', 0),
    ('2026-02-07', 'pescado_al_gusto', 1310,       'especial',   'pescado', 0),
    ('2026-02-07', 'enchiladas',       995,        'complemento','none',    0),
]

total = 0
for date, slot, dish_id, cg, protein, is_forced in week_menu:
    if dish_id is None:
        print(f'  SKIP {date} {slot}: no dish_id')
        continue
    d = conn.execute('SELECT name FROM dish WHERE id=?', (dish_id,)).fetchone()
    dish_name = d[0] if d else f'???[{dish_id}]'
    conn.execute(
        'INSERT INTO menu_item (menu_week_id, menu_date, slot, dish_id, is_forced, was_exception, exception_reason) '
        'VALUES (?,?,?,?,?,0,NULL)',
        (week_id, date, slot, dish_id, is_forced)
    )
    total += 1
    print(f'  [{date}] {slot}: {dish_name}')

conn.commit()
conn.close()
print(f'\nDone. {total} menu_items insertados, semana {WEEK_START} finalizada.')
